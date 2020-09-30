# Step 1: rename conflicting Metadata node properties

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

# Step 2: copy all Metadata node properties to Entity node

Since we have lots of nodes, it's advisable to perform the operation in smaller batches. Here is an example of limiting the operation to 1000 at a time.

````
MATCH (E:Entity) - [:HAS_METADATA] -> (M:Metadata)
WITH E, M
LIMIT 1000
SET E += M
RETURN E, M
````

# Step 3: copy all Metadata node properties to Activity node

````
MATCH (A:Activity) - [:HAS_METADATA] -> (M:Metadata)
WITH A, M
LIMIT 1000
SET A += M
RETURN A, M
````

# Step 4: normalize Entity node properties

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

# Step 5: normalize Activity node properties

````
MATCH (A:Activity)
SET 
    A.activity_type = A.activitytype
REMOVE 
    A.activitytype
RETURN A
````

# Step 6: normalize Collection node properties

````
MATCH (C:Collection)
SET 
    C.entity_type = C.entitytype
REMOVE 
    C.entitytype
RETURN C
````

# Step 7: delete all Metadata nodes and all HAS_METADATA relationships

This action will all the Metadata nodes and any relationship (HAS_METADATA is the only one) going to or from it.

````
MATCH (M:Metadata)
DETACH DELETE M
````

# Step 8: Get rid off unwanted property keys, labels, and indices

Use https://github.com/jexp/store-utils which is an offline process to read our graph database and copy its (contents, nodes, relationships) to a new graph database and only include property keys associated with nodes.
