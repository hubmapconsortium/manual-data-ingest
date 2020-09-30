# Rename conflicting Metadata node properties

````
MATCH (m:Metadata)
SET m.metadata_entitytype = m.entitytype, 
    m.metadata_uuid = m.uuid, 
    m.metadata_label = m.label,
    m.metadata_provenance_create_timestamp = m.provenance_create_timestamp,
    m.metadata_modified_create_timestamp = m.provenance_modified_timestamp
REMOVE m.entitytype, 
    m.uuid, 
    m.label, 
    m.provenance_create_timestamp, 
    m.provenance_modified_timestamp
RETURN m
````

# Copy all Metadata node properties to Entity node

````
MATCH (e:Entity {entitytype:"Donor"}) - [:HAS_METADATA] -> (m:Metadata)
SET e += m
RETURN e, m
````

````
MATCH (e:Entity {entitytype:"Dataset"}) - [:HAS_METADATA] -> (m:Metadata)
SET e += m
RETURN e, m
````
