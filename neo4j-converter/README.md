# Step 1: drop all old indexes

List all the current indexes with the following query:

````
CALL db.indexes()
````

Try to drop all the indexes with:

````
CALL apoc.schema.assert({},{},true) YIELD label, key 
RETURN *
````
If encounter any errors, try to drop them individually:

````
CALL  db.index.fulltext.drop("indexName")
````

# Step 2: rename conflicting Metadata node properties

````
MATCH (M:Metadata)
SET 
    M.metadata_entitytype = M.entitytype, 
    M.metadata_uuid = M.uuid, 
    M.metadata_label = M.label,
    M.metadata_provenance_create_timestamp = M.provenance_create_timestamp,
    M.metadata_provenance_modified_timestamp = M.provenance_modified_timestamp
REMOVE 
    M.entitytype, 
    M.uuid, 
    M.label, 
    M.provenance_create_timestamp, 
    M.provenance_modified_timestamp
RETURN M
````

# Step 3: copy all Metadata node properties to Entity node

Since we have lots of nodes, it's advisable to perform the operation in smaller batches. Here is an example of limiting the operation to 1000 at a time.

````
MATCH (E:Entity) - [:HAS_METADATA] -> (M:Metadata)
WITH E, M
LIMIT 1000
SET E += M
RETURN E, M
````

# Step 4: copy all Metadata node properties to Activity node

````
MATCH (A:Activity) - [:HAS_METADATA] -> (M:Metadata)
WITH A, M
LIMIT 1000
SET A += M
RETURN A, M
````

# Step 5: normalize Entity node properties

````
MATCH (E:Entity)
SET 
    E.entity_type = E.entitytype
REMOVE 
    E.entitytype,
    E.metadata_entitytype,
    E.metadata_uuid
RETURN E
````

# Step 6: normalize Activity node properties

````
MATCH (A:Activity)
SET 
    A.activity_type = A.activitytype
REMOVE 
    A.activitytype
RETURN A
````

# Step 7: normalize Collection node properties

````
MATCH (C:Collection)
SET 
    C.entity_type = C.entitytype
REMOVE 
    C.entitytype
RETURN C
````

# Step 8: delete all Metadata nodes and all HAS_METADATA relationships

This action will all the Metadata nodes and any relationship (HAS_METADATA is the only one) going to or from it.

````
MATCH (M:Metadata)
DETACH DELETE M
```
