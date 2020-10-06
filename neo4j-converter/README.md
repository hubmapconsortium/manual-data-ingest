# Neo4j Node Properties Migration and Renaming

Standardize the naming of node properties across Neo4j, Elasticsearch, and API services.

## Back up the Neo4j database

Make a backup of the source Neo4j graph database first. There are two options to execute the following steps:

- Option 1: make all the changes against the source database
- Option 2: import the backup database into another Neo4j server and make the changes. And once all done, replace the source database with the modified database.

## Step 1: drop all indexes

There are two types of indexes in Neo4j:

- Single-property index: an index that is created on a single property for any given label.

- Composite index: an index that is created on more than one property for any given label.

List all the current indexes with the following query:

````
CALL db.indexes()
````

If there's at least one composite index, we firs need to drop them individually using their `indexName` from the result:

````
CALL  db.index.fulltext.drop("targetIndexName")
````

Once the composite indexes are gone, we drop all the rest of the single-property index in one call:

````
CALL apoc.schema.assert({},{},true) YIELD label, key 
RETURN *
````

Once all indexes dropped, verify with 

````
call db.indexes()
````

## Step 2: find and delete orphan nodes

````
MATCH (n)
WHERE NOT (n)--() 
RETURN n
````

It is okay to delete the orphaned Metadata and Collection nodes. But do not delete the orphaned Entity nodes as these are Lab nodes which haven't been used yet (but will be soon).

If all the resulting orphan nodes can be deleted, do it with:

````
MATCH (n:Metadata)
WHERE NOT (n)--()
DELETE n
````

````
MATCH (n:Collection)
WHERE NOT (n)--()
DELETE n
````

## Step 3: normalize Metadata node properties

Questions: 
1. Metadata, Entity, and Activity all have the `provenance_create_timestamp` property, but this property in Metadata and Activity is not getting converted in the https://github.com/hubmapconsortium/search-api/blob/master/src/elasticsearch/neo4j-to-es-attributes.json
2. How to handle `ingest_metadata`, `specimen_metadata`? In the https://github.com/hubmapconsortium/search-api/blob/master/src/elasticsearch/neo4j-to-es-attributes.json, they both get mapped to `metadata`. And the original `metadata` is also mapped to `metadata`.
3. Cypher query `MATCH (n:Entity {entitytype: "Sample"})- [:HAS_METADATA]-> (m:Metadata) RETURN n, m` shows that lots of Entity nodes share the same Metadata, why?

**Property keys to be renamed**

| Current Property Key            | New Property Key                     |
|---------------------------------|--------------------------------------|
| lab\_tissue\_id                 | lab\_tissue\_sample\_id              |
| image\_file\_metadata           | portal\_uploaded\_image\_files       |
| label                           | lab\_name                            |
| metadatas                       | portal\_metadata\_upload\_files      |
| phi                             | contains\_human\_genetic\_sequences  |
| protocol                        | protocol\_url                        |
| provenance\_group\_uuid         | group\_uuid                          |
| provenance\_modified\_timestamp | last\_modified\_timestamp            |
| provenance\_user\_displayname   | created\_by\_user\_displayname       |
| provenance\_user\_email         | created\_by\_user\_email             |

**Property keys to be deleted without renaming**

| Property Key                 |
|------------------------------|
| entitytype                   |
| creator\_email               |
| creator\_name                |
| dataset\_collection\_uuid    |
| globus\_directory\_url\_path |
| group\_name                  |
| group\_uuid                  |
| is\_protected                |
| metadata\_file               |
| reference\_uuid              |
| source\_uuid                 |
| source\_uuids                |
| user\_group\_uuid            |
| uuid                         |

````
CALL apoc.periodic.iterate(
    "MATCH (M:Metadata) RETURN M", 
    "SET 
        // Rename property keys
        M.hubmap_id = M.display_doi,
        M.doi_suffix_id = M.doi,
        M.dedi_name = M.label,
        M.local_directory_rel_path = M.local_directory_url_path,
        M.pipeline_message = M.message,
        M.portal_metadata_upload_files = M.metadatas,
        M.dataset_name = M.name,
        M.contains_human_genetic_sequences = M.phi,
        M.protocol_url = M.protocol,
        M.protocol_info =M.protocols,
        M.create_timestamp = M.provenance_create_timestamp,
        M.group_uuid = M.provenance_group_uuid,
        M.last_modified_user_displayname = M.provenance_last_updated_user_displayname,
        M.last_modified_user_email = M.provenance_last_updated_user_email,
        M.last_modified_user_sub = M.provenance_last_updated_user_sub,
        M.last_modified_timestamp = M.provenance_modified_timestamp,
        M.created_by_user_displayname = M.provenance_user_displayname,
        M.created_by_user_email = M.provenance_user_email,
        M.created_by_user_sub = M.provenance_user_sub
    REMOVE 
        // Remove properties that have been renamed
        M.display_doi,
        M.doi,
        M.label,
        M.local_directory_url_path,
        M.message,
        M.metadatas,
        M.name,
        M.phi,
        M.protocol,
        M.protocols,
        M.provenance_create_timestamp,
        M.provenance_group_uuid,
        M.provenance_last_updated_user_displayname,
        M.provenance_last_updated_user_email,
        M.provenance_last_updated_user_sub,
        M.provenance_modified_timestamp,
        M.provenance_user_displayname,
        M.provenance_user_email,
        M.provenance_user_sub,
        // Remove the flowwing properties directly without copying to Entity/Activity nodes
        M.entitytype, 
        M.collection_uuid,
        M.creator_email,
        M.creator_name,
        M.dataset_collection_uuid,
        M.globus_directory_url_path,
        M.group_name,
        M.group_uuid,
        M.is_protected,
        M.metadata_file,
        M.reference_uuid,
        M.source_uuid,
        M.source_uuids,
        M.user_group_uuid,
        M.uuid, 
        M.provenance_create_timestamp", 
    {batchSize:1000}
)
YIELD batches, total, timeTaken, committedOperations, failedOperations
RETURN batches, total, timeTaken, committedOperations, failedOperations
````

## Step 4: copy all Metadata node properties to Entity node

Since we have lots of nodes, it's advisable to perform the operation in smaller batches. Here is an example of limiting the operation to 1000 at a time.

````
CALL apoc.periodic.iterate(
    "MATCH (E:Entity) - [:HAS_METADATA] -> (M:Metadata) RETURN E, M", 
    "SET E += M", 
    {batchSize:1000}
)
YIELD batches, total, timeTaken, committedOperations, failedOperations
RETURN batches, total, timeTaken, committedOperations, failedOperations
````

## Step 5: copy all Metadata node properties to Activity node

````
CALL apoc.periodic.iterate(
    "MATCH (A:Activity) - [:HAS_METADATA] -> (M:Metadata) RETURN A, M", 
    "SET A += M", 
    {batchSize:1000}
    
)
YIELD batches, total, timeTaken, committedOperations, failedOperations
RETURN batches, total, timeTaken, committedOperations, failedOperations
````

## Step 6: normalize Entity node properties

**Property keys to be renamed**

| Current Property Key          | New Property Key     |
|-------------------------------|----------------------|
| entitytype                    | entity\_type         |
| hubmap\_identifier            | hubmap\_display\_id  |
| provenance\_create\_timestamp | create\_timestamp    |

````
CALL apoc.periodic.iterate(
    "MATCH (E:Entity) RETURN E", 
    "SET 
        // Rename property keys based on 
        // https://github.com/hubmapconsortium/search-api/blob/master/src/elasticsearch/neo4j-to-es-attributes.json
        E.entity_type = E.entitytype,
        E.hubmap_display_id = E.hubmap_identifier,
        E.create_timestamp = E.provenance_create_timestamp
    REMOVE 
        // Remove properties(key/value) that have been renamed
        E.entitytype,
        E.hubmap_identifier,
        E.provenance_create_timestamp", 
    {batchSize:1000}
)
YIELD batches, total, timeTaken, committedOperations, failedOperations
RETURN batches, total, timeTaken, committedOperations, failedOperations
````

Veryfy the new property keys by `entity_type`:

````
MATCH (p:Entity {entity_type: "Donor"})
WITH distinct p, keys(p) as pKeys
UNWIND pKeys as Key
RETURN distinct labels(p), Key, apoc.map.get(apoc.meta.cypher.types(p), Key, [true])
````

````
MATCH (p:Entity {entity_type: "Sample"})
WITH distinct p, keys(p) as pKeys
UNWIND pKeys as Key
RETURN distinct labels(p), Key, apoc.map.get(apoc.meta.cypher.types(p), Key, [true])
````

````
MATCH (p:Entity {entity_type: "Dataset"})
WITH distinct p, keys(p) as pKeys
UNWIND pKeys as Key
RETURN distinct labels(p), Key, apoc.map.get(apoc.meta.cypher.types(p), Key, [true])
````

## Step 7: normalize Activity node properties

**Property keys to be renamed**

| Current Property Key | New Property Key |
|----------------------|------------------|
| activitytype         | creation\_action |

````
CALL apoc.periodic.iterate(
    "MATCH (A:Activity) RETURN A", 
    "SET 
        // Rename property keys based on 
        // https://github.com/hubmapconsortium/search-api/blob/master/src/elasticsearch/neo4j-to-es-attributes.json
        A.creation_action = A.activitytype
    REMOVE 
        // Remove properties(key/value) that have been renamed
        A.activitytype", 
    {batchSize:1000}
)
YIELD batches, total, timeTaken, committedOperations, failedOperations
RETURN batches, total, timeTaken, committedOperations, failedOperations
````

Veryfy the new property keys:

````
MATCH (p:Activity)
WITH distinct p, keys(p) as pKeys
UNWIND pKeys as Key
RETURN distinct labels(p), Key, apoc.map.get(apoc.meta.cypher.types(p), Key, [true])
````

## Step 8: normalize Collection node properties

**Property keys to be renamed**

| Current Property Key | New Property Key |
|----------------------|------------------|
| entitytype           | entity\_type     |

````
CALL apoc.periodic.iterate(
    "MATCH (C:Collection) RETURN C", 
    "SET 
        C.entity_type = C.entitytype
    REMOVE 
        C.entitytype", 
    {batchSize:1000}
)
YIELD batches, total, timeTaken, committedOperations, failedOperations
RETURN batches, total, timeTaken, committedOperations, failedOperations
````

Veryfy the new property keys:

````
MATCH (p:Collection)
WITH distinct p, keys(p) as pKeys
UNWIND pKeys as Key
RETURN distinct labels(p), Key, apoc.map.get(apoc.meta.cypher.types(p), Key, [true])
````

## Step 9: delete all Metadata nodes and all HAS_METADATA relationships

This action will delete all the Metadata nodes and any relationship (HAS_METADATA is the only one) going to or from it.

````
CALL apoc.periodic.iterate(
    "MATCH (M:Metadata) RETURN M", 
    "DETACH DELETE M", 
    {batchSize:1000}
)
YIELD batches, total, timeTaken, committedOperations, failedOperations
RETURN batches, total, timeTaken, committedOperations, failedOperations
````

At this point, all the Metadata nodes and any relationship (HAS_METADATA is the only one) going to or from it should have been deleted from the database. The `total` number of deleted Metadata nodes should match the total number returned from Step 1.

## Step 10: Recreate indexes

Based on the search needs, recreate either single-property index or composite index. Best practice is to give the index a name when it is created. More info: https://neo4j.com/docs/cypher-manual/current/administration/indexes-for-search-performance/

## Why do those deleted property keys still appear?

After completing the above steps, you may notice that some of the deleted property keys still appear on the left panel of the Neo4j browser even though they are no longer associated with any nodes. This is expected. Unlike labels and relationship types which have underlying meta-data that report the number of objects for each, there is no meta-data for property keys.

## Create new labels based on `entity_type` if desired

````
match (n:Entity {entity_type:"Dataset"})
set n :Dataset
return n
````

````
match (n:Entity {entity_type:"Sample"})
set n :Sample
return n
````

````
match (n:Entity {entity_type:"Donor"})
set n :Donor
return n
````
