"""
data_loader.py - reads JSONL from named subfolders into SQLite
"""
import json, os, sqlite3, logging
logger = logging.getLogger(__name__)

FOLDER_MAP = {
    "sales_order_headers": "sales_orders",
    "sales_order_items": "sales_order_items",
    "sales_order_schedule_lines": "sales_order_schedule_lines",
    "outbound_delivery_headers": "delivery_headers",
    "outbound_delivery_items": "delivery_items",
    "billing_document_headers": "billing_headers",
    "billing_document_items": "billing_items",
    "billing_document_cancellations": "billing_cancellations",
    "journal_entry_items_accounts_receivable": "journal_entries",
    "business_partners": "business_partners",
    "business_partner_addresses": "business_partner_addresses",
    "customer_company_assignments": "customers",
    "customer_sales_area_assignments": "customer_sales_areas",
    "payments_accounts_receivable": "payments",
    "products": "products",
    "product_descriptions": "product_descriptions",
    "product_plants": "product_plants",
    "product_storage_locations": "product_storage_locations",
    "plants": "plants",
}

def create_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sales_orders (
        salesOrder TEXT PRIMARY KEY, salesOrderType TEXT, salesOrganization TEXT,
        distributionChannel TEXT, organizationDivision TEXT, soldToParty TEXT,
        creationDate TEXT, createdByUser TEXT, lastChangeDateTime TEXT,
        totalNetAmount REAL, overallDeliveryStatus TEXT, overallOrdReltdBillgStatus TEXT,
        transactionCurrency TEXT, requestedDeliveryDate TEXT, customerPaymentTerms TEXT,
        headerBillingBlockReason TEXT, deliveryBlockReason TEXT,
        incotermsClassification TEXT, incotermsLocation1 TEXT);
    CREATE TABLE IF NOT EXISTS sales_order_items (
        salesOrder TEXT, salesOrderItem TEXT, material TEXT, orderQuantity REAL,
        orderQuantityUnit TEXT, netAmount REAL, plant TEXT, storageLocation TEXT,
        requestedDeliveryDate TEXT, PRIMARY KEY (salesOrder, salesOrderItem));
    CREATE TABLE IF NOT EXISTS sales_order_schedule_lines (
        salesOrder TEXT, salesOrderItem TEXT, scheduleLine TEXT,
        requestedDeliveryDate TEXT, scheduledQuantity REAL,
        PRIMARY KEY (salesOrder, salesOrderItem, scheduleLine));
    CREATE TABLE IF NOT EXISTS delivery_headers (
        deliveryDocument TEXT PRIMARY KEY, creationDate TEXT, shippingPoint TEXT,
        overallGoodsMovementStatus TEXT, overallPickingStatus TEXT,
        headerBillingBlockReason TEXT, deliveryBlockReason TEXT, actualGoodsMovementDate TEXT);
    CREATE TABLE IF NOT EXISTS delivery_items (
        deliveryDocument TEXT, deliveryDocumentItem TEXT, actualDeliveryQuantity REAL,
        deliveryQuantityUnit TEXT, plant TEXT, referenceSdDocument TEXT,
        referenceSdDocumentItem TEXT, storageLocation TEXT,
        PRIMARY KEY (deliveryDocument, deliveryDocumentItem));
    CREATE TABLE IF NOT EXISTS billing_headers (
        billingDocument TEXT PRIMARY KEY, billingDocumentType TEXT, creationDate TEXT,
        billingDocumentDate TEXT, totalNetAmount REAL, transactionCurrency TEXT,
        companyCode TEXT, fiscalYear TEXT, accountingDocument TEXT, soldToParty TEXT,
        billingDocumentIsCancelled INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS billing_items (
        billingDocument TEXT, billingDocumentItem TEXT, material TEXT,
        billingQuantity REAL, billingQuantityUnit TEXT, netAmount REAL,
        transactionCurrency TEXT, referenceSdDocument TEXT, referenceSdDocumentItem TEXT,
        PRIMARY KEY (billingDocument, billingDocumentItem));
    CREATE TABLE IF NOT EXISTS billing_cancellations (
        billingDocument TEXT PRIMARY KEY, cancelledBillingDocument TEXT,
        creationDate TEXT, companyCode TEXT);
    CREATE TABLE IF NOT EXISTS journal_entries (
        accountingDocument TEXT, accountingDocumentItem TEXT, companyCode TEXT,
        fiscalYear TEXT, glAccount TEXT, referenceDocument TEXT, costCenter TEXT,
        profitCenter TEXT, transactionCurrency TEXT, amountInTransactionCurrency REAL,
        postingDate TEXT, documentDate TEXT, accountingDocumentType TEXT, customer TEXT,
        clearingDate TEXT, clearingAccountingDocument TEXT, financialAccountType TEXT,
        PRIMARY KEY (accountingDocument, accountingDocumentItem));
    CREATE TABLE IF NOT EXISTS business_partners (
        businessPartner TEXT PRIMARY KEY, customer TEXT, businessPartnerCategory TEXT,
        businessPartnerFullName TEXT, businessPartnerName TEXT, organizationBpName1 TEXT,
        creationDate TEXT, businessPartnerIsBlocked INTEGER DEFAULT 0,
        isMarkedForArchiving INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS business_partner_addresses (
        businessPartner TEXT, addressId TEXT, streetName TEXT, cityName TEXT,
        country TEXT, region TEXT, postalCode TEXT,
        PRIMARY KEY (businessPartner, addressId));
    CREATE TABLE IF NOT EXISTS customers (
        customer TEXT PRIMARY KEY, companyCode TEXT, reconciliationAccount TEXT,
        customerAccountGroup TEXT, deletionIndicator INTEGER DEFAULT 0, paymentTerms TEXT);
    CREATE TABLE IF NOT EXISTS customer_sales_areas (
        customer TEXT, salesOrganization TEXT, distributionChannel TEXT,
        division TEXT, customerGroup TEXT,
        PRIMARY KEY (customer, salesOrganization, distributionChannel, division));
    CREATE TABLE IF NOT EXISTS payments (
        accountingDocument TEXT, accountingDocumentItem TEXT, companyCode TEXT,
        fiscalYear TEXT, customer TEXT, amountInTransactionCurrency REAL,
        transactionCurrency TEXT, postingDate TEXT, dueDate TEXT,
        paymentMethod TEXT, clearingDocument TEXT,
        PRIMARY KEY (accountingDocument, accountingDocumentItem));
    CREATE TABLE IF NOT EXISTS products (
        product TEXT PRIMARY KEY, language TEXT, productDescription TEXT);
    CREATE TABLE IF NOT EXISTS product_descriptions (
        product TEXT, language TEXT, productDescription TEXT,
        PRIMARY KEY (product, language));
    CREATE TABLE IF NOT EXISTS product_plants (
        product TEXT, plant TEXT, availabilityCheckType TEXT,
        PRIMARY KEY (product, plant));
    CREATE TABLE IF NOT EXISTS product_storage_locations (
        product TEXT, plant TEXT, storageLocation TEXT,
        PRIMARY KEY (product, plant, storageLocation));
    CREATE TABLE IF NOT EXISTS plants (
        plant TEXT PRIMARY KEY, plantName TEXT, salesOrganization TEXT,
        distributionChannel TEXT, factoryCalendar TEXT, addressId TEXT, language TEXT);
    """)
    conn.commit()

def sf(v):
    try: return float(v) if v not in (None,"","null") else None
    except: return None

def sb(v):
    if isinstance(v,bool): return 1 if v else 0
    if isinstance(v,str): return 1 if v.lower() in ("true","1","yes") else 0
    return 0

def insert_record(conn, folder, obj):
    try:
        if folder=="sales_order_headers":
            conn.execute("INSERT OR REPLACE INTO sales_orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                obj.get("salesOrder"),obj.get("salesOrderType"),obj.get("salesOrganization"),
                obj.get("distributionChannel"),obj.get("organizationDivision"),obj.get("soldToParty"),
                obj.get("creationDate"),obj.get("createdByUser"),obj.get("lastChangeDateTime"),
                sf(obj.get("totalNetAmount")),obj.get("overallDeliveryStatus"),
                obj.get("overallOrdReltdBillgStatus"),obj.get("transactionCurrency"),
                obj.get("requestedDeliveryDate"),obj.get("customerPaymentTerms"),
                obj.get("headerBillingBlockReason"),obj.get("deliveryBlockReason"),
                obj.get("incotermsClassification"),obj.get("incotermsLocation1")))
        elif folder=="sales_order_items":
            conn.execute("INSERT OR REPLACE INTO sales_order_items VALUES(?,?,?,?,?,?,?,?,?)",(
                obj.get("salesOrder"),obj.get("salesOrderItem"),obj.get("material"),
                sf(obj.get("orderQuantity")),obj.get("orderQuantityUnit"),sf(obj.get("netAmount")),
                obj.get("plant"),obj.get("storageLocation"),obj.get("requestedDeliveryDate")))
        elif folder=="sales_order_schedule_lines":
            conn.execute("INSERT OR REPLACE INTO sales_order_schedule_lines VALUES(?,?,?,?,?)",(
                obj.get("salesOrder"),obj.get("salesOrderItem"),obj.get("scheduleLine"),
                obj.get("requestedDeliveryDate"),sf(obj.get("scheduledQuantity"))))
        elif folder=="outbound_delivery_headers":
            conn.execute("INSERT OR REPLACE INTO delivery_headers VALUES(?,?,?,?,?,?,?,?)",(
                obj.get("deliveryDocument"),obj.get("creationDate"),obj.get("shippingPoint"),
                obj.get("overallGoodsMovementStatus"),obj.get("overallPickingStatus"),
                obj.get("headerBillingBlockReason"),obj.get("deliveryBlockReason"),
                obj.get("actualGoodsMovementDate")))
        elif folder=="outbound_delivery_items":
            conn.execute("INSERT OR REPLACE INTO delivery_items VALUES(?,?,?,?,?,?,?,?)",(
                obj.get("deliveryDocument"),obj.get("deliveryDocumentItem"),
                sf(obj.get("actualDeliveryQuantity")),obj.get("deliveryQuantityUnit"),
                obj.get("plant"),obj.get("referenceSdDocument"),
                obj.get("referenceSdDocumentItem"),obj.get("storageLocation")))
        elif folder=="billing_document_headers":
            conn.execute("INSERT OR REPLACE INTO billing_headers VALUES(?,?,?,?,?,?,?,?,?,?,?)",(
                obj.get("billingDocument"),obj.get("billingDocumentType"),obj.get("creationDate"),
                obj.get("billingDocumentDate"),sf(obj.get("totalNetAmount")),
                obj.get("transactionCurrency"),obj.get("companyCode"),obj.get("fiscalYear"),
                obj.get("accountingDocument"),obj.get("soldToParty"),
                sb(obj.get("billingDocumentIsCancelled"))))
        elif folder=="billing_document_items":
            conn.execute("INSERT OR REPLACE INTO billing_items VALUES(?,?,?,?,?,?,?,?,?)",(
                obj.get("billingDocument"),obj.get("billingDocumentItem"),obj.get("material"),
                sf(obj.get("billingQuantity")),obj.get("billingQuantityUnit"),
                sf(obj.get("netAmount")),obj.get("transactionCurrency"),
                obj.get("referenceSdDocument"),obj.get("referenceSdDocumentItem")))
        elif folder=="billing_document_cancellations":
            conn.execute("INSERT OR REPLACE INTO billing_cancellations VALUES(?,?,?,?)",(
                obj.get("billingDocument"),obj.get("cancelledBillingDocument"),
                obj.get("creationDate"),obj.get("companyCode")))
        elif folder=="journal_entry_items_accounts_receivable":
            conn.execute("INSERT OR REPLACE INTO journal_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                obj.get("accountingDocument"),obj.get("accountingDocumentItem"),
                obj.get("companyCode"),obj.get("fiscalYear"),obj.get("glAccount"),
                obj.get("referenceDocument"),obj.get("costCenter"),obj.get("profitCenter"),
                obj.get("transactionCurrency"),sf(obj.get("amountInTransactionCurrency")),
                obj.get("postingDate"),obj.get("documentDate"),obj.get("accountingDocumentType"),
                obj.get("customer"),obj.get("clearingDate"),
                obj.get("clearingAccountingDocument"),obj.get("financialAccountType")))
        elif folder=="business_partners":
            conn.execute("INSERT OR REPLACE INTO business_partners VALUES(?,?,?,?,?,?,?,?,?)",(
                obj.get("businessPartner"),obj.get("customer"),obj.get("businessPartnerCategory"),
                obj.get("businessPartnerFullName"),obj.get("businessPartnerName"),
                obj.get("organizationBpName1"),obj.get("creationDate"),
                sb(obj.get("businessPartnerIsBlocked")),sb(obj.get("isMarkedForArchiving"))))
        elif folder=="business_partner_addresses":
            conn.execute("INSERT OR REPLACE INTO business_partner_addresses VALUES(?,?,?,?,?,?,?)",(
                obj.get("businessPartner"),obj.get("addressId"),obj.get("streetName"),
                obj.get("cityName"),obj.get("country"),obj.get("region"),obj.get("postalCode")))
        elif folder=="customer_company_assignments":
            conn.execute("INSERT OR REPLACE INTO customers VALUES(?,?,?,?,?,?)",(
                obj.get("customer"),obj.get("companyCode"),obj.get("reconciliationAccount"),
                obj.get("customerAccountGroup"),sb(obj.get("deletionIndicator")),
                obj.get("paymentTerms")))
        elif folder=="customer_sales_area_assignments":
            conn.execute("INSERT OR REPLACE INTO customer_sales_areas VALUES(?,?,?,?,?)",(
                obj.get("customer"),obj.get("salesOrganization"),obj.get("distributionChannel"),
                obj.get("division"),obj.get("customerGroup")))
        elif folder=="payments_accounts_receivable":
            conn.execute("INSERT OR REPLACE INTO payments VALUES(?,?,?,?,?,?,?,?,?,?,?)",(
                obj.get("accountingDocument"),obj.get("accountingDocumentItem"),
                obj.get("companyCode"),obj.get("fiscalYear"),obj.get("customer"),
                sf(obj.get("amountInTransactionCurrency")),obj.get("transactionCurrency"),
                obj.get("postingDate"),obj.get("dueDate"),obj.get("paymentMethod"),
                obj.get("clearingDocument")))
        elif folder=="products":
            conn.execute("INSERT OR REPLACE INTO products VALUES(?,?,?)",(
                obj.get("product"),obj.get("language"),obj.get("productDescription")))
        elif folder=="product_descriptions":
            conn.execute("INSERT OR REPLACE INTO product_descriptions VALUES(?,?,?)",(
                obj.get("product"),obj.get("language"),obj.get("productDescription")))
        elif folder=="product_plants":
            conn.execute("INSERT OR REPLACE INTO product_plants VALUES(?,?,?)",(
                obj.get("product"),obj.get("plant"),obj.get("availabilityCheckType")))
        elif folder=="product_storage_locations":
            conn.execute("INSERT OR REPLACE INTO product_storage_locations VALUES(?,?,?)",(
                obj.get("product"),obj.get("plant"),obj.get("storageLocation")))
        elif folder=="plants":
            conn.execute("INSERT OR REPLACE INTO plants VALUES(?,?,?,?,?,?,?)",(
                obj.get("plant"),obj.get("plantName"),obj.get("salesOrganization"),
                obj.get("distributionChannel"),obj.get("factoryCalendar"),
                obj.get("addressId"),obj.get("language")))
    except Exception as e:
        logger.warning(f"Insert failed [{folder}]: {e}")

def load_all_data(conn, data_dir):
    counts = {}
    for folder in sorted(os.listdir(data_dir)):
        folder_path = os.path.join(data_dir, folder)
        if not os.path.isdir(folder_path) or folder not in FOLDER_MAP:
            continue
        n = 0
        for fname in os.listdir(folder_path):
            if not fname.endswith(".jsonl"): continue
            with open(os.path.join(folder_path, fname), encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line: continue
                    try:
                        insert_record(conn, folder, json.loads(line))
                        n += 1
                    except: continue
        counts[folder] = n
        logger.info(f"  {folder}: {n} rows")
    conn.commit()
    return counts

def init_database(db_path, data_dir=None):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    create_tables(conn)
    if conn.execute("SELECT COUNT(*) FROM sales_orders").fetchone()[0] == 0:
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        logger.info(f"Loading data from: {data_dir}")
        load_all_data(conn, data_dir)
    else:
        logger.info("Database already loaded")
    return conn