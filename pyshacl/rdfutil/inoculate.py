from itertools import chain
from typing import Optional, Union

import rdflib

from .clone import clone_blank_node, clone_graph
from .consts import RDF, ConjunctiveLike, GraphLike, OWL_classes, OWL_properties, RDFS_classes, RDFS_properties


def inoculate(data_graph: rdflib.Graph, ontology: rdflib.Graph):
    """
    Copies all RDFS and OWL axioms (classes, relationship definitions, and properties)
    from the ontology graph into the data_graph.
    :param data_graph:
    :type data_graph:
    :param ontology:
    :type ontology:
    :return:
    :rtype:
    """
    copied_bnode_map = {}

    for ont_class in chain(RDFS_classes, OWL_classes):
        found_s = list(ontology.subjects(RDF.type, ont_class))
        for s in found_s:
            if isinstance(s, rdflib.BNode):
                if s in copied_bnode_map:
                    new_bnode = copied_bnode_map[s]
                else:
                    new_bnode = clone_blank_node(ontology, s, data_graph)
                    copied_bnode_map[s] = new_bnode
                new_s = new_bnode
            else:
                new_s = s
            data_graph.add((new_s, RDF.type, ont_class))

    for ont_property in chain(RDFS_properties, OWL_properties):
        found_s_o = list(ontology.subject_objects(ont_property))
        for s, o in found_s_o:
            if isinstance(s, rdflib.BNode):
                if s in copied_bnode_map:
                    new_bnode = copied_bnode_map[s]
                else:
                    new_bnode = clone_blank_node(ontology, s, data_graph)
                    copied_bnode_map[s] = new_bnode
                new_s = new_bnode
            else:
                new_s = s

            if isinstance(o, rdflib.BNode):
                if o in copied_bnode_map:
                    new_bnode = copied_bnode_map[o]
                else:
                    new_bnode = clone_blank_node(ontology, o, data_graph)
                    copied_bnode_map[o] = new_bnode
                new_o = new_bnode
            else:
                new_o = o

            data_graph.add((new_s, ont_property, new_o))
    return data_graph


def inoculate_dataset(
    base_ds: ConjunctiveLike, ontology_ds: GraphLike, target_ds: Optional[Union[ConjunctiveLike, str]] = None
):
    """
    Make a clone of base_ds (dataset) and add RDFS and OWL triples from ontology_ds
    :param base_ds:
    :type base_ds: rdflib.Dataset
    :param ontology_ds:
    :type ontology_ds: rdflib.Dataset
    :param target_ds:
    :type target_ds: rdflib.Dataset|str|NoneType
    :return: The cloned Dataset with ontology triples from ontology_ds
    :rtype: rdflib.Dataset
    """

    # TODO: Decide whether we need to clone base_ds before calling this,
    # or we clone base_ds as part of this function
    default_union = base_ds.default_union
    base_named_graphs = list(base_ds.contexts())
    base_default_context = base_ds.default_context.identifier
    if target_ds is None:
        target_ds = rdflib.Dataset(default_union=default_union)
    elif target_ds == "inplace" or target_ds == "base":
        target_ds = base_ds
    elif isinstance(target_ds, str):
        raise RuntimeError("target_ds cannot be a string (unless it is 'inplace' or 'base')")
    if isinstance(target_ds, (rdflib.ConjunctiveGraph, rdflib.Dataset)):
        if not isinstance(target_ds, rdflib.Dataset):
            raise RuntimeError("Cannot inoculate ConjunctiveGraph, use Dataset instead.")
    else:
        raise RuntimeError("Cannot inoculate datasets if target_ds passed in is not a Dataset itself.")
    if isinstance(ontology_ds, (rdflib.Dataset, rdflib.ConjunctiveGraph)):
        ont_graphs = list(ontology_ds.contexts())
        ont_default_context = ontology_ds.default_context.identifier
    else:
        ont_graphs = [ontology_ds]
        ont_default_context = None
    if target_ds is base_ds or target_ds == "inplace" or target_ds == "base":
        target_ds = base_ds
        for bg in base_named_graphs:
            if len(base_named_graphs) > 1 and bg.identifier == base_default_context and len(bg) < 1:
                # skip empty default named graph in base_graph
                continue
            for og in ont_graphs:
                if len(ont_graphs) > 1 and og.identifier == ont_default_context and len(og) < 1:
                    # skip empty default named graph in ontology_graph
                    continue
                inoculate(bg, og)
    else:
        inoculated_graphs = {}
        for bg in base_named_graphs:
            if len(base_named_graphs) > 1 and bg.identifier == base_default_context and len(bg) < 1:
                # skip empty default named graph in base_graph
                continue
            target_g = rdflib.Graph(store=target_ds.store, identifier=bg.identifier)
            clone_g = clone_graph(bg, target_graph=target_g)
            for og in ont_graphs:
                if len(ont_graphs) > 1 and og.identifier == ont_default_context and len(og) < 1:
                    # skip empty default named graph in ontology_graph
                    continue
                inoculate(clone_g, og)
            inoculated_graphs[bg.identifier] = clone_g
        default_context_id = target_ds.default_context.identifier
        for i, m in inoculated_graphs.items():
            if i == default_context_id:
                target_ds.store.remove_graph(target_ds.default_context)
                target_ds.default_context = m
            target_ds.add_graph(m)
    return target_ds