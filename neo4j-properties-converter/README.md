# Step 1: rename conflicting Metadata node properties

````
MATCH (m:Metadata)
SET m.metadata_entitytype = m.entitytype, 
    m.metadata_uuid = m.uuid, 
    m.metadata_label = m.label,
    m.metadata_provenance_create_timestamp = m.provenance_create_timestamp,
    m.metadata_provenance_modified_timestamp = m.provenance_modified_timestamp
REMOVE m.entitytype, 
    m.uuid, 
    m.label, 
    m.provenance_create_timestamp, 
    m.provenance_modified_timestamp
RETURN m
````

# Step 2: copy all Metadata node properties to Entity node

Since we have lots of nodes, it's advisable to perform the operation in smaller batches. Here is an example of limiting the operation to 1000 at a time.

````
MATCH (e:Entity) - [:HAS_METADATA] -> (m:Metadata)
WITH e, m
LIMIT 1000
SET e += m
RETURN e, m
````
