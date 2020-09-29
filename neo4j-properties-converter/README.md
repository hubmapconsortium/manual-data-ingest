# Rename conflicting Metadata node properties

````
MATCH (m:Metadata)
SET m.metadata_entitytype = m.entitytype, m.metadata_uuid = m.uuid, m.metadata_label = m.label
REMOVE m.entitytype, m.uuid, m.label
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