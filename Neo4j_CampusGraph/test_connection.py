
from neo4j import GraphDatabase

# 1. Connection information
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "learnneo4j")

# 2. Create driver
driver = GraphDatabase.driver(URI, auth=AUTH)

try:
    # 3. Verify connection
    driver.verify_connectivity()
    print("Connected to Neo4j successfully!")

    # 4. Execute a Cypher query
    records, summary, keys = driver.execute_query(
        "RETURN 'Hello from Python' AS message"
    )

    # 5. Display result
    for record in records:
        print(record["message"])

finally:
    # 6. Close connection
    driver.close()
