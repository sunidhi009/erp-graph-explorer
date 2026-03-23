"""
graph_builder.py
Builds a graph of nodes and edges from the SQLite database.
Each entity (SalesOrder, Delivery, Billing, JournalEntry, Customer, Product, Plant)
becomes a node. Relationships become edges.
"""

import sqlite3
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Color scheme per node type
NODE_COLORS = {
    "SalesOrder":      "#4A90D9",
    "Delivery":        "#27AE60",
    "BillingDocument": "#E67E22",
    "JournalEntry":    "#9B59B6",
    "Customer":        "#E74C3C",
    "Product":         "#1ABC9C",
    "Plant":           "#F39C12",
    "BusinessPartner": "#34495E",
}

NODE_SIZES = {
    "SalesOrder":      18,
    "Delivery":        15,
    "BillingDocument": 15,
    "JournalEntry":    12,
    "Customer":        20,
    "Product":         10,
    "Plant":           14,
    "BusinessPartner": 16,
}


def build_graph(conn: sqlite3.Connection, max_nodes: int = 300) -> dict:
    """
    Build a graph dict with 'nodes' and 'links' arrays.
    Limits to max_nodes for performance in the UI.
    """
    nodes = {}
    links = []
    seen_links = set()

    def add_node(node_id: str, node_type: str, label: str, metadata: dict):
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "type": node_type,
                "label": label,
                "color": NODE_COLORS.get(node_type, "#888"),
                "size": NODE_SIZES.get(node_type, 12),
                "metadata": metadata,
            }

    def add_link(source: str, target: str, relation: str):
        key = f"{source}→{target}→{relation}"
        if key not in seen_links and source in nodes and target in nodes:
            seen_links.add(key)
            links.append({"source": source, "target": target, "relation": relation})

    # ── Customers ──────────────────────────────────────────────────────────
    rows = conn.execute("SELECT * FROM customers LIMIT 50").fetchall()
    for r in rows:
        cid = r["customer"]
        add_node(cid, "Customer", f"Customer {cid}", dict(r))

    # ── Business Partners (enrich customer nodes with company name) ─────────
    rows = conn.execute("SELECT * FROM business_partners LIMIT 50").fetchall()
    for r in rows:
        bp_id = r["businessPartner"]
        label = r["businessPartnerName"] or f"Partner {bp_id}"
        meta = dict(r)
        add_node(bp_id, "BusinessPartner", label, meta)
        # BusinessPartner → Customer
        if r["customer"]:
            add_node(r["customer"], "Customer", f"Customer {r['customer']}", {"customer": r["customer"]})
            add_link(bp_id, r["customer"], "IS_CUSTOMER")

    # ── Plants ─────────────────────────────────────────────────────────────
    rows = conn.execute("SELECT * FROM plants LIMIT 50").fetchall()
    for r in rows:
        add_node(r["plant"], "Plant", r["plantName"] or r["plant"], dict(r))

    # ── Products (sample — there are thousands) ───────────────────────────
    rows = conn.execute("SELECT * FROM products LIMIT 60").fetchall()
    for r in rows:
        label = (r["productDescription"] or r["product"])[:30]
        add_node(r["product"], "Product", label, dict(r))

    # ── Sales Orders ───────────────────────────────────────────────────────
    rows = conn.execute("""
        SELECT * FROM sales_orders
        ORDER BY creationDate DESC
        LIMIT 80
    """).fetchall()
    for r in rows:
        so_id = r["salesOrder"]
        add_node(so_id, "SalesOrder",
                 f"SO {so_id}",
                 {**dict(r), "amount": r["totalNetAmount"]})
        # SalesOrder → Customer
        if r["soldToParty"]:
            party = r["soldToParty"]
            if party not in nodes:
                add_node(party, "Customer", f"Customer {party}", {"customer": party})
            add_link(r["soldToParty"], so_id, "PLACED_ORDER")

    # ── Delivery Items → link SO to Delivery ──────────────────────────────
    rows = conn.execute("""
        SELECT di.deliveryDocument, di.referenceSdDocument, di.plant,
               dh.overallGoodsMovementStatus, dh.overallPickingStatus, dh.shippingPoint,
               dh.creationDate
        FROM delivery_items di
        LEFT JOIN delivery_headers dh ON di.deliveryDocument = dh.deliveryDocument
        LIMIT 200
    """).fetchall()
    for r in rows:
        dd = r["deliveryDocument"]
        meta = {
            "deliveryDocument": dd,
            "shippingPoint": r["shippingPoint"],
            "overallGoodsMovementStatus": r["overallGoodsMovementStatus"],
            "overallPickingStatus": r["overallPickingStatus"],
            "creationDate": r["creationDate"],
        }
        add_node(dd, "Delivery", f"Delivery {dd}", meta)
        # SalesOrder → Delivery
        if r["referenceSdDocument"] and r["referenceSdDocument"] in nodes:
            add_link(r["referenceSdDocument"], dd, "DELIVERED_VIA")
        # Delivery → Plant
        if r["plant"] and r["plant"] in nodes:
            add_link(dd, r["plant"], "SHIPPED_FROM")

    # ── Billing Headers ────────────────────────────────────────────────────
    rows = conn.execute("""
        SELECT * FROM billing_headers
        ORDER BY creationDate DESC
        LIMIT 100
    """).fetchall()
    for r in rows:
        bd = r["billingDocument"]
        add_node(bd, "BillingDocument",
                 f"Billing {bd}",
                 {**dict(r), "cancelled": bool(r["billingDocumentIsCancelled"])})

    # ── Billing Items → link Delivery to Billing ──────────────────────────
    rows = conn.execute("""
        SELECT bi.billingDocument, bi.referenceSdDocument, bi.material, bi.netAmount
        FROM billing_items bi
        LIMIT 300
    """).fetchall()
    for r in rows:
        bd = r["billingDocument"]
        if bd not in nodes:
            add_node(bd, "BillingDocument", f"Billing {bd}", {"billingDocument": bd})
        # Delivery → Billing
        if r["referenceSdDocument"] and r["referenceSdDocument"] in nodes:
            add_link(r["referenceSdDocument"], bd, "BILLED_AS")
        # Billing → Product
        if r["material"] and r["material"] in nodes:
            add_link(bd, r["material"], "INCLUDES_PRODUCT")

    # ── Journal Entries ────────────────────────────────────────────────────
    rows = conn.execute("""
        SELECT accountingDocument, accountingDocumentItem, referenceDocument,
               amountInTransactionCurrency, transactionCurrency, postingDate, customer
        FROM journal_entries
        LIMIT 100
    """).fetchall()
    for r in rows:
        je_id = r["accountingDocument"]
        if je_id not in nodes:
            add_node(je_id, "JournalEntry",
                     f"JE {je_id}",
                     dict(r))
        # BillingDocument → JournalEntry
        if r["referenceDocument"] and r["referenceDocument"] in nodes:
            add_link(r["referenceDocument"], je_id, "POSTED_TO")

    node_list = list(nodes.values())
    logger.info(f"Graph: {len(node_list)} nodes, {len(links)} links")

    return {
        "nodes": node_list,
        "links": links,
        "stats": {
            "total_nodes": len(node_list),
            "total_links": len(links),
            "by_type": _count_by_type(node_list),
        }
    }


def get_node_neighbors(conn: sqlite3.Connection, node_id: str, node_type: str) -> dict:
    """Return neighbors and full metadata for a specific node."""
    metadata = {}
    related_ids = []

    if node_type == "SalesOrder":
        row = conn.execute("SELECT * FROM sales_orders WHERE salesOrder=?", (node_id,)).fetchone()
        if row:
            metadata = dict(row)
        # Find deliveries
        deliveries = conn.execute("""
            SELECT DISTINCT deliveryDocument FROM delivery_items
            WHERE referenceSdDocument=?
        """, (node_id,)).fetchall()
        related_ids = [r["deliveryDocument"] for r in deliveries]

    elif node_type == "Delivery":
        row = conn.execute("SELECT * FROM delivery_headers WHERE deliveryDocument=?", (node_id,)).fetchone()
        if row:
            metadata = dict(row)
        items = conn.execute("SELECT * FROM delivery_items WHERE deliveryDocument=?", (node_id,)).fetchall()
        metadata["items"] = [dict(i) for i in items]
        # Find billings
        billings = conn.execute("""
            SELECT DISTINCT billingDocument FROM billing_items
            WHERE referenceSdDocument=?
        """, (node_id,)).fetchall()
        related_ids = [r["billingDocument"] for r in billings]

    elif node_type == "BillingDocument":
        row = conn.execute("SELECT * FROM billing_headers WHERE billingDocument=?", (node_id,)).fetchone()
        if row:
            metadata = dict(row)
        items = conn.execute("SELECT * FROM billing_items WHERE billingDocument=?", (node_id,)).fetchall()
        metadata["items"] = [dict(i) for i in items]
        # Find journal entries
        journals = conn.execute("""
            SELECT DISTINCT accountingDocument FROM journal_entries
            WHERE referenceDocument=?
        """, (node_id,)).fetchall()
        related_ids = [r["accountingDocument"] for r in journals]

    elif node_type == "Customer":
        row = conn.execute("SELECT * FROM customers WHERE customer=?", (node_id,)).fetchone()
        if row:
            metadata = dict(row)
        # Check business partner
        bp = conn.execute("SELECT * FROM business_partners WHERE customer=?", (node_id,)).fetchone()
        if bp:
            metadata["companyName"] = bp["businessPartnerName"]
        # Sales orders
        orders = conn.execute("""
            SELECT salesOrder FROM sales_orders WHERE soldToParty=? LIMIT 10
        """, (node_id,)).fetchall()
        related_ids = [r["salesOrder"] for r in orders]

    return {"metadata": metadata, "related_ids": related_ids}


def _count_by_type(nodes: list) -> dict:
    counts = {}
    for n in nodes:
        t = n["type"]
        counts[t] = counts.get(t, 0) + 1
    return counts