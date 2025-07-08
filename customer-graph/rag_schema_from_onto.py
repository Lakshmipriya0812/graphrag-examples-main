from rdflib import Graph, URIRef, XSD
from rdflib.namespace import RDF, OWL, RDFS
from neo4j_graphrag.experimental.components.schema import (
    SchemaBuilder,
    NodeType,
    PropertyType,
    RelationshipType,
)


def getLocalPart(uri):
  pos = -1
  pos = uri.rfind('#') 
  if pos < 0 :
    pos = uri.rfind('/')  
  if pos < 0 :
    pos = uri.rindex(':')
  return uri[pos+1:]



def getNLOntology(g):
  result = ''
  definedcats = []

  result += '\nNode Labels:\n'
  for cat in g.subjects(RDF.type, OWL.Class):  
    result += getLocalPart(cat)
    definedcats.append(cat)
    for desc in g.objects(cat,RDFS.comment):
        result += ': ' + desc + '\n'
  extracats = {}
  for cat in g.objects(None,RDFS.domain):
     if not cat in definedcats:
        extracats[cat] = None
  for cat in g.objects(None,RDFS.range):
     if not (cat.startswith("http://www.w3.org/2001/XMLSchema#") or cat in definedcats):
        extracats[cat] = None   
  
  for xtracat in extracats.keys():
     result += getLocalPart(cat) + ":\n"

  result += '\nNode Properties:\n'
  for att in g.subjects(RDF.type, OWL.DatatypeProperty):  
    result += getLocalPart(att)
    for dom in g.objects(att,RDFS.domain):
        result += ': Attribute that applies to entities of type ' + getLocalPart(dom)  
    for desc in g.objects(att,RDFS.comment):
        result += '. It represents ' + desc + '\n'

  result += '\nRelationships:\n'
  for att in g.subjects(RDF.type, OWL.ObjectProperty):  
    result += getLocalPart(att)
    for dom in g.objects(att,RDFS.domain):
        result += ': Relationship that connects entities of type ' + getLocalPart(dom)
    for ran in g.objects(att,RDFS.range):
        result += ' to entities of type ' + getLocalPart(ran)
    for desc in g.objects(att,RDFS.comment):
        result += '. It represents ' + desc + '\n'
  return result



def getPropertiesForClass(g, cat):
  props = []
  for dtp in g.subjects(RDFS.domain,cat):
    if (dtp, RDF.type, OWL.DatatypeProperty) in g:
      propName = getLocalPart(dtp)
      propDesc = next(g.objects(dtp, RDFS.comment),"")
      props.append(PropertyType(name=propName,
                                  type=convert_to_di_data_type(next(g.objects(dtp, RDFS.range),"")),
                                  description=propDesc))
  return props

def getSchemaFromOnto(path):
    g = Graph()
    g.parse(path)
    schema_builder = SchemaBuilder()

    classes = {}
    node_types = []
    relationship_types = []
    patterns = []

    for cat in g.subjects(RDF.type, OWL.Class):
        classes[cat] = None
        label = getLocalPart(cat)
        props = getPropertiesForClass(g, cat)
        node_types.append(NodeType(
            label=label,
            description=next(g.objects(cat, RDFS.comment), ""),
            properties=props
        ))

    for cat in g.objects(None, RDFS.domain):
        if cat not in classes:
            classes[cat] = None
            label = getLocalPart(cat)
            props = getPropertiesForClass(g, cat)
            node_types.append(NodeType(
                label=label,
                description=next(g.objects(cat, RDFS.comment), ""),
                properties=props
            ))

    for cat in g.objects(None, RDFS.range):
        if not (cat.startswith("http://www.w3.org/2001/XMLSchema#") or cat in classes):
            classes[cat] = None
            label = getLocalPart(cat)
            props = getPropertiesForClass(g, cat)
            node_types.append(NodeType(
                label=label,
                description=next(g.objects(cat, RDFS.comment), ""),
                properties=props
            ))

    for op in g.subjects(RDF.type, OWL.ObjectProperty):
        relname = getLocalPart(op)
        relationship_types.append(RelationshipType(
            label=relname,
            description=next(g.objects(op, RDFS.comment), ""),
            properties=[]
        ))

    for op in g.subjects(RDF.type, OWL.ObjectProperty):
        relname = getLocalPart(op)
        doms = [getLocalPart(d) for d in g.objects(op, RDFS.domain) if d in classes]
        rans = [getLocalPart(r) for r in g.objects(op, RDFS.range) if r in classes]
        for d in doms:
            for r in rans:
                patterns.append((d, relname, r))

    return schema_builder.create_schema_model(
        node_types=node_types,
        relationship_types=relationship_types,
        patterns=patterns
    )


def getPKs(g):
  keys = []
  for k in g.subjects(RDF.type, OWL.InverseFunctionalProperty):  
    keys.append(getLocalPart(k))
  return keys


def convert_to_di_data_type(datatype):
  if datatype in {XSD.integer, XSD.int, XSD.positiveInteger, XSD.negativeInteger, XSD.nonPositiveInteger,
                  XSD.nonNegativeInteger, XSD.long, XSD.short, XSD.unsignedLong, XSD.unsignedShort}:
      return "INTEGER"
  elif datatype in {XSD.decimal, XSD.float, XSD.double}:
      return "FLOAT"
  elif datatype == XSD.boolean:
      return "BOOLEAN"
  #elif datatype == XSD.dateTime:
  #    return "LOCAL_DATETIME"
  else:
      return "STRING"