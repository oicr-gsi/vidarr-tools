import argparse

import json
import os
import sys
from typing import Dict, Any
import WDL

_output_mapping = [
    (WDL.Type.File(),
     "file"),
    (WDL.Type.Array(
        WDL.Type.File(), nonempty=True),
     "files"),
    (WDL.Type.Pair(
        WDL.Type.File(),
        WDL.Type.Map(
            (WDL.Type.String(), WDL.Type.String()))),
     "file-with-labels"),
    (WDL.Type.Pair(
        WDL.Type.Array(
            WDL.Type.File(), nonempty=True),
        WDL.Type.Map(
            (WDL.Type.String(),
             WDL.Type.String()))),
     "files-with-labels"),
    (WDL.Type.Array(
        WDL.Type.Pair(
            WDL.Type.File(),
            WDL.Type.Map(
                (WDL.Type.String(),
                 WDL.Type.String()))), nonempty=True),
     "files-with-labels"),
    (WDL.Type.Boolean(),
     "quality-control"),
    (WDL.Type.File(
        optional=True),
     "optional-file"),
    (WDL.Type.Array(WDL.Type.File(), optional=True, nonempty=True),
     "optional-files"),
    (WDL.Type.Array(WDL.Type.File(), optional=True, nonempty=False),
     "optional-files"),
    (WDL.Type.Array(
        WDL.Type.File(),
        nonempty=False),
     "optional-files"),
    (WDL.Type.Pair(
        WDL.Type.File(),
        WDL.Type.Map(
            (WDL.Type.String(),
             WDL.Type.String())),
        optional=True),
     "optional-file-with-labels"),
    (WDL.Type.Pair(
        WDL.Type.Array(WDL.Type.File(), nonempty=True),
        WDL.Type.Map(
            (WDL.Type.String(),
             WDL.Type.String())),
        optional=True),
     "optional-files-with-labels"),
    (WDL.Type.Boolean(
        optional=True),
     "optional-quality-control"),
]


def _map_input(wdl_type: WDL.Type.Base, structures: Dict[str, Any]):
    if wdl_type.optional:
        return {
            "is": "optional",
            "inner": _map_inner_input(
                wdl_type,
                structures)}
    else:
        return _map_inner_input(wdl_type, structures)


def _map_inner_input(wdl_type: WDL.Type.Base, structures: Dict[str, Any]):
    if isinstance(wdl_type, WDL.Type.Array):
        (inner,) = wdl_type.parameters
        return {"is": "list", "inner": _map_input(inner, structures)}
    elif isinstance(wdl_type, WDL.Type.Pair):
        (left_type, right_type) = wdl_type.parameters
        return {
            "is": "pair", "left": _map_input(
                left_type, structures), "right": _map_input(
                right_type, structures)}
    elif isinstance(wdl_type, WDL.Type.StructInstance):
        return {"is": "object", "fields": structures[wdl_type.type_name]}
    elif isinstance(wdl_type, WDL.Type.Map):
        (key_type, value_type) = wdl_type.parameters
        return {
            "is": "dictionary", "key": _map_input(
                key_type, structures), "value": _map_input(
                value_type, structures)}
    elif isinstance(wdl_type, WDL.Type.Boolean):
        return "boolean"
    elif isinstance(wdl_type, WDL.Type.Directory):
        return "directory"
    elif isinstance(wdl_type, WDL.Type.File):
        return "file"
    elif isinstance(wdl_type, WDL.Type.Float):
        return "floating"
    elif isinstance(wdl_type, WDL.Type.Int):
        return "integer"
    elif isinstance(wdl_type, WDL.Type.String):
        return "string"
    raise ValueError(f"No conversion for {wdl_type}")


def _map_output(wdl_type: WDL.Type.Base, allow_complex: bool,
                structures: WDL.Env.Bindings[WDL.StructTypeDef]):
    for (vidarr_wdl_type, vidarr_type) in _output_mapping:
        if wdl_type == vidarr_wdl_type:
            return vidarr_type
    if allow_complex and isinstance(wdl_type, WDL.Type.Array):
        (inner,) = wdl_type.parameters
        if isinstance(inner, WDL.Type.StructInstance):
            keys = {}
            outputs = {}
            for (member_name,
                 member_type) in structures[inner.type_name].members.items():
                if member_type == WDL.Type.Int():
                    keys[member_name] = "INTEGER"
                elif member_type == WDL.Type.String():
                    keys[member_name] = "STRING"
                else:
                    outputs[member_name] = _map_output(
                        member_type, False, structures)
            return {"is": "list", "keys": keys, "outputs": outputs}
    raise ValueError(
        f"Vidarr cannot process output type {wdl_type} in output.")


def parse(wdl_file_path: str) -> Dict[str, Any]:
    """
    Read a WDL file and convert it into a Vidarr workflow definition

    :param wdl_file_path: the path to the WDL file; this must be a path on disk in case the WDL file imports other files
    :return: the Vidarr configuration object
    """
    return convert(WDL.load(wdl_file_path))


def convert(doc: WDL.Document) -> Dict[str, Any]:
    """
    Convert a parsed WDL file into a Vidarr workflow definition
    :param doc:  the parsed WDL file
    :return: the Vidarr configuration object
    """
    workflow_name = doc.workflow.name
    structures = {}
    unprocessed_structs = [s for s in doc.struct_typedefs]
    while unprocessed_structs:
        structs_needing_unprocessed = []
        for structure in unprocessed_structs:
            try:
                structures[structure.name] = {member_name: _map_input(member_type, structures) for (
                    member_name, member_type) in structure.value.members.items()}
            except KeyError:
                structs_needing_unprocessed.append(structure)
        assert len(structs_needing_unprocessed) < len(unprocessed_structs)
        unprocessed_structs = structs_needing_unprocessed

    workflow_inputs = {}

    def read_output(output: WDL.Decl):
        output_metadata = doc.workflow.meta.get(
            "output_meta", {}).get(
            output.name, {})
        if isinstance(
                output_metadata,
                dict) and "vidarr_type" in output_metadata:
            return output_metadata["vidarr_type"]
        else:
            return _map_output(
                output.type, True, doc.struct_typedefs)

    for wf_input in (doc.workflow.available_inputs or []):
        meta = doc.workflow.parameter_meta.get(wf_input.name)
        if meta and isinstance(meta, dict) and "vidarr_type" in meta:
            workflow_inputs[doc.workflow.name + "." +
                            wf_input.name] = meta["vidarr_type"]
        else:
            workflow_inputs[doc.workflow.name + "." + wf_input.name] = {"is": "optional", "inner": _map_input(
                wf_input.value.type, structures)} if wf_input.value.expr else _map_input(wf_input.value.type, structures)

    workflow = {
        'language': 'WDL_' + str(
            doc.wdl_version).replace(
            ".",
            "_"),
        'outputs': {
            workflow_name + "." + output.name:
            read_output(output)
            for output in doc.workflow.outputs},
        'parameters': workflow_inputs,
        'workflow': doc.source_text,
        'accessoryFiles': {
            imported.uri: imported.doc.source_text for imported in doc.imports}}
    return workflow


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-i",
        "--input-wdl-path",
        required=True,
        help="Source wdl path")
    parser.add_argument(
        "-o",
        "--output-path",
        required=False,
        help="Output a file with contents of the workflow parameter dict")
    args = parser.parse_args()

    if args.output_path:
        workflow = parse(args.input_wdl_path)
        parent_dir = os.path.dirname(args.output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(args.output_path, "w") as output_file:
            json.dump(workflow, output_file)
    else:
        json.dump(
            parse(
                args.input_wdl_path),
            sys.stdout,
            indent=4,
            sort_keys=True)


if __name__ == "__main__":
    main()
