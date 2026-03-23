"""
main.py — FastAPI backend for ERP Graph System
"""
import os
import logging
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data_loader import init_database
from graph_builder import build_graph, get_node_neighbors
from llm_handler import enrich_answer_with_data, get_schema_summary

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ERP Graph System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Init DB once on startup ───────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "erp.db"))
conn = init_database(DB_PATH, data_dir=os.getenv("DATA_DIR"))  
_graph_cache = None

def get_graph():
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = build_graph(conn)
    return _graph_cache

# ── Models ────────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    message: str
    history: list = []

class NodeExpandRequest(BaseModel):
    node_id: str
    node_type: str

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    counts = get_schema_summary(conn)
    graph = get_graph()
    return {
        "status": "ok",
        "database": counts,
        "graph": {
            "nodes": graph["stats"]["total_nodes"],
            "links": graph["stats"]["total_links"],
            "by_type": graph["stats"]["by_type"],
        }
    }

@app.get("/api/graph")
def graph_data():
    return get_graph()

@app.post("/api/graph/expand")
def expand_node(req: NodeExpandRequest):
    return get_node_neighbors(conn, req.node_id, req.node_type)

@app.post("/api/chat")
def chat(msg: ChatMessage):
    if not msg.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    result = enrich_answer_with_data(conn, msg.message, conversation_history=msg.history)
    return result

@app.get("/api/stats")
def stats():
    """Quick stats for dashboard cards."""
    so_count = conn.execute("SELECT COUNT(*) FROM sales_orders").fetchone()[0]
    so_amount = conn.execute("SELECT COALESCE(SUM(totalNetAmount),0) FROM sales_orders").fetchone()[0]
    del_count = conn.execute("SELECT COUNT(DISTINCT deliveryDocument) FROM delivery_headers").fetchone()[0]
    bil_count = conn.execute("SELECT COUNT(*) FROM billing_headers WHERE billingDocumentIsCancelled=0").fetchone()[0]
    je_count  = conn.execute("SELECT COUNT(DISTINCT accountingDocument) FROM journal_entries").fetchone()[0]
    cust_count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    prod_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    # Broken flows: delivered but not billed
    broken = conn.execute("""
        SELECT COUNT(DISTINCT di.referenceSdDocument) FROM delivery_items di
        LEFT JOIN billing_items bi ON bi.referenceSdDocument = di.deliveryDocument
        WHERE bi.billingDocument IS NULL
    """).fetchone()[0]

    return {
        "salesOrders": so_count,
        "totalRevenue": round(so_amount, 2),
        "deliveries": del_count,
        "billingDocs": bil_count,
        "journalEntries": je_count,
        "customers": cust_count,
        "products": prod_count,
        "brokenFlows": broken,
    }

@app.get("/api/top-products")
def top_products():
    """Products with highest billing count."""
    rows = conn.execute("""
        SELECT bi.material as product,
               COALESCE(p.productDescription, bi.material) as name,
               COUNT(*) as billingCount,
               SUM(bi.netAmount) as totalAmount
        FROM billing_items bi
        LEFT JOIN products p ON p.product = bi.material
        GROUP BY bi.material
        ORDER BY billingCount DESC
        LIMIT 10
    """).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/broken-flows")
def broken_flows():
    """Sales orders with incomplete O2C flows."""
    # Delivered but not billed
    rows = conn.execute("""
        SELECT DISTINCT
            di.referenceSdDocument as salesOrder,
            di.deliveryDocument,
            'Delivered but not billed' as issue
        FROM delivery_items di
        LEFT JOIN billing_items bi ON bi.referenceSdDocument = di.deliveryDocument
        WHERE bi.billingDocument IS NULL
        LIMIT 20
    """).fetchall()
    result = [dict(r) for r in rows]

    # Billed but no journal entry
    rows2 = conn.execute("""
        SELECT DISTINCT
            bh.billingDocument,
            bh.soldToParty as customer,
            'Billed but no journal entry' as issue
        FROM billing_headers bh
        LEFT JOIN journal_entries je ON je.referenceDocument = bh.billingDocument
        WHERE je.accountingDocument IS NULL
          AND bh.billingDocumentIsCancelled = 0
        LIMIT 20
    """).fetchall()
    result += [dict(r) for r in rows2]
    return result

@app.get("/api/trace/{billing_id}")
def trace_billing(billing_id: str):
    """Trace full O2C flow for a billing document."""
    bh = conn.execute("SELECT * FROM billing_headers WHERE billingDocument=?", (billing_id,)).fetchone()
    if not bh:
        raise HTTPException(404, "Billing document not found")
    bh = dict(bh)

    # Get delivery items that reference this billing
    items = conn.execute("SELECT * FROM billing_items WHERE billingDocument=?", (billing_id,)).fetchall()
    deliveries = list({i["referenceSdDocument"] for i in items if i["referenceSdDocument"]})

    # Get sales orders from delivery items
    sales_orders = []
    for d in deliveries:
        rows = conn.execute(
            "SELECT DISTINCT referenceSdDocument FROM delivery_items WHERE deliveryDocument=?", (d,)
        ).fetchall()
        sales_orders += [r["referenceSdDocument"] for r in rows if r["referenceSdDocument"]]

    # Get journal entries
    journals = conn.execute(
        "SELECT * FROM journal_entries WHERE referenceDocument=?", (billing_id,)
    ).fetchall()

    # Get customer name
    customer_name = None
    if bh.get("soldToParty"):
        bp = conn.execute(
            "SELECT businessPartnerName FROM business_partners WHERE customer=?",
            (bh["soldToParty"],)
        ).fetchone()
        if bp:
            customer_name = bp["businessPartnerName"]

    return {
        "billingDocument": bh,
        "deliveries": deliveries,
        "salesOrders": list(set(sales_orders)),
        "journalEntries": [dict(j) for j in journals],
        "customerName": customer_name,
    }