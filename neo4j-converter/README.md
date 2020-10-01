# Back up the Neo4j database

Make a backup of the source Neo4j graph database first. There are two options to execute the following steps:

- Option 1: make all the changes against the source database
- Option 2: import the backup database into another Neo4j server and make the changes. And once all done, replace the source database with the modified database.

# Step 1: drop all indexes

There are two types of indexes in Neo4j:

- Single-property index: an index that is created on a single property for any given label.

- Composite index: an index that is created on more than one property for any given label.

List all the current indexes with the following query:

````
CALL db.indexes()
````

If all the returned indexes are single-property index, drop all the indexes with:

````
CALL apoc.schema.assert({},{},true) YIELD label, key 
RETURN *
````

If there's at least one composite index, we firs need to drop them individually using their `indexName` from the result:

````
CALL  db.index.fulltext.drop("targetIndexName")
````

Then once the composite indexes are gone, we drop all the rest of the single-property index in one call:

````
CALL apoc.schema.assert({},{},true) YIELD label, key 
RETURN *
````

Once all indexes dropped, verify with 

````
call db.indexes()
````

# Step 2: rename conflicting Metadata node properties

````
CALL apoc.periodic.iterate(
    "MATCH (M:Metadata) RETURN M", 
    "SET 
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
        M.provenance_modified_timestamp", 
    {batchSize:1000}
)
YIELD batches, total 
RETURN batches, total
````

# Step 3: copy all Metadata node properties to Entity node

Since we have lots of nodes, it's advisable to perform the operation in smaller batches. Here is an example of limiting the operation to 1000 at a time.

````
CALL apoc.periodic.iterate(
    "MATCH (E:Entity) - [:HAS_METADATA] -> (M:Metadata) RETURN E, M", 
    "SET E += M", 
    {batchSize:1000}
)
YIELD batches, total 
RETURN batches, total
````

# Step 4: copy all Metadata node properties to Activity node

````
CALL apoc.periodic.iterate(
    "MATCH (A:Activity) - [:HAS_METADATA] -> (M:Metadata) RETURN A, M", 
    "SET A += M", 
    {batchSize:1000}
)
YIELD batches, total 
RETURN batches, total
````

# Step 5: normalize Entity node properties

````
CALL apoc.periodic.iterate(
    "MATCH (E:Entity) RETURN E", 
    "SET 
        E.entity_type = E.entitytype,
        E.hubmap_display_id = E.hubmap_identifier,
        E.create_timestamp = E.provenance_create_timestamp,
        E.portal_uploaded_image_files = E.image_file_metadata,
        E.lab_name = E.label,
        E.portal_metadata_upload_files = E.metadatas,
        E.contains_human_genetic_sequences = E.phi,
        E.protocol_url = E.protocol,
        E.group_uuid = E.provenance_group_uuid,
        E.last_modified_timestamp = E.provenance_modified_timestamp,
        E.created_by_user_displayname = E.provenance_user_displayname,
        E.created_by_user_email = E.provenance_user_email,
    REMOVE 
        E.entitytype,
        E.hubmap_identifier,
        E.provenance_create_timestamp,
        E.image_file_metadata,
        E.label,
        E.metadatas,
        E.phi,
        E.protocol,
        E.provenance_group_uuid,
        E.provenance_modified_timestamp,
        E.provenance_user_displayname,
        E.provenance_user_email,
        E.metadata_entitytype,
        E.metadata_uuid,
        E.metadata_label", 
    {batchSize:1000}
)
YIELD batches, total 
RETURN batches, total
````

# Step 6: normalize Activity node properties

````
CALL apoc.periodic.iterate(
    "MATCH (A:Activity) RETURN A", 
    "SET 
        A.creation_action = A.activitytype
    REMOVE 
        A.activitytype", 
    {batchSize:1000}
)
YIELD batches, total 
RETURN batches, total
````

# Step 7: normalize Collection node properties

````
CALL apoc.periodic.iterate(
    "MATCH (C:Collection) RETURN C", 
    "SET 
        C.entity_type = C.entitytype
    REMOVE 
        C.entitytype", 
    {batchSize:1000}
)
YIELD batches, total 
RETURN batches, total
````

# Step 8: delete all Metadata nodes and all HAS_METADATA relationships

This action will all the Metadata nodes and any relationship (HAS_METADATA is the only one) going to or from it.

````
CALL apoc.periodic.iterate(
    "MATCH (M:Metadata) RETURN M", 
    "DETACH DELETE M", 
    {batchSize:1000}
)
YIELD batches, total 
RETURN batches, total
````

At this point, all the Metadata nodes and any relationship (HAS_METADATA is the only one) going to or from it should have been deleted from the database. The `total` number of deleted Metadata nodes should match the total number returned from Step 1.

# Why do those deleted property keys still appear?

After completing the above steps, you may notice that some of the deleted property keys still appear on the left panel of the Neo4j browser even though they are no longer associated with any nodes. This is expected. Unlike labels and relationship types which have underlying meta-data that report the number of objects for each, there is no meta-data for property keys.
