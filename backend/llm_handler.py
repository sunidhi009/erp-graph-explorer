import os, sqlite3, json, re, logging, httpx
logger = logging.getLogger(__name__)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are an ERP SQL analyst. Answer ONLY questions about this SQLite database:
sales_orders(salesOrder,soldToParty,totalNetAmount,overallDeliveryStatus,creationDate)
delivery_headers(deliveryDocument,shippingPoint,overallGoodsMovementStatus)
delivery_items(deliveryDocument,deliveryDocumentItem,plant,referenceSdDocument,actualDeliveryQuantity)
billing_headers(billingDocument,soldToParty,totalNetAmount,accountingDocument,billingDocumentIsCancelled)
billing_items(billingDocument,material,netAmount,referenceSdDocument)
journal_entries(accountingDocument,referenceDocument,amountInTransactionCurrency,customer)
customers(customer,companyCode)
business_partners(businessPartner,customer,businessPartnerName)
products(product,productDescription)
plants(plant,plantName)
JOINS: sales_orders.soldToParty=customers.customer=business_partners.customer, delivery_items.referenceSdDocument=sales_orders.salesOrder, billing_items.referenceSdDocument=delivery_headers.deliveryDocument, journal_entries.referenceDocument=billing_headers.billingDocument
Return ONLY this JSON: {"answer":"text","sql":"SELECT...","rows":[],"referenced_ids":[],"is_off_topic":false}
If not about ERP data set is_off_topic=true."""


def call_gemini(prompt, conversation_history=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    try:
        resp = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq error: {e} | {resp.text if 'resp' in dir() else ''}")
        return json.dumps({"answer": f"LLM error: {str(e)}", "sql": None, "rows": [], "referenced_ids": [], "is_off_topic": False})


def extract_json(text):
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text).strip()
    try:
        return json.loads(text)
    except:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except:
            pass
    return {"answer": text, "sql": None, "rows": [], "referenced_ids": [], "is_off_topic": False}


def execute_sql_safely(conn, sql):
    if not sql: return [], None
    if not sql.strip().upper().startswith("SELECT"):
        return [], "Only SELECT allowed."
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchmany(20)], None
    except Exception as e:
        return [], str(e)


def enrich_answer_with_data(conn, user_message, conversation_history=None):
    result = extract_json(call_gemini(f"Question: {user_message}\nReturn JSON only."))
    if result.get("sql") and not result.get("is_off_topic"):
        rows, error = execute_sql_safely(conn, result["sql"])
        if error:
            result2 = extract_json(call_gemini(f"Fix SQL error: {error}\nSQL: {result['sql']}\nReturn JSON only."))
            if result2.get("sql"):
                rows2, err2 = execute_sql_safely(conn, result2["sql"])
                if not err2:
                    result2["rows"] = rows2
                    return result2
        else:
            result["rows"] = rows
    return result


def get_schema_summary(conn):
    tables = ["sales_orders","delivery_headers","delivery_items","billing_headers",
              "billing_items","journal_entries","customers","business_partners","products","plants"]
    counts = {}
    for t in tables:
        try: counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except: counts[t] = 0
    return counts