import argparse
import json
import os
import sys
import re
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


def _map_output(doc: WDL.Document, output: WDL.Decl, wdl_type: WDL.Type.Base, allow_complex: bool,
                structures: WDL.Env.Bindings[WDL.StructTypeDef]):
    output_metadata = doc.workflow.meta.get("output_meta", {}).get(output.name, {})
    for (vidarr_wdl_type, vidarr_type) in _output_mapping:
        if wdl_type == vidarr_wdl_type:
            if isinstance(output_metadata, dict) and "vidarr_label" in output_metadata:
                if isinstance(wdl_type, WDL.Type.File) and not output.type.optional:
                    return "file-with-labels"
                elif isinstance(wdl_type, WDL.Type.File) and output.type.optional:
                    return "optional-file-with-labels"
                elif vidarr_type == "file-with-labels":
                    vidarr_label = WDL.Expr.String(parts=['"', 'vidarr_label', '"'], pos=output.expr.right.items[0][0].pos)
                    vidarr_label_value = WDL.Expr.String(parts=['"', output_metadata['vidarr_label'], '"'], pos=output.expr.right.items[0][0].pos)

                    # Extracting existing entries from output.expr.right
                    existing_entries = output.expr.right.items

                    # Constructing a list of existing entries
                    existing_entries_list = []
                    for item in existing_entries:
                        existing_entries_list.append(item)

                    # Adding the new (vidarr_label, vidarr_label_value) tuple
                    existing_entries_list.append((vidarr_label, vidarr_label_value))

                    # Creating a new map with the updated list of items
                    new_map = WDL.Expr.Map(pos=output.expr.pos, items=existing_entries_list)
                    output.expr.right = new_map

                else:
                    raise ValueError(f"vidarr_label does not support {wdl_type}")
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
                        doc, output, member_type, False, structures)
            return {"is": "list", "keys": keys, "outputs": outputs}
    raise ValueError(
        f"Vidarr cannot process output type {wdl_type} in output.")


def parse(wdl_file_path: str) -> Dict[str, Any]:
    """
    Read a WDL file and convert it into a Vidarr workflow definition

    :param wdl_file_path: the path to the WDL file; this must be a path on disk in case the WDL file imports other files
    :return: the Vidarr configuration object
    """
    try:
        doc = WDL.load(wdl_file_path)
    except (WDL.Error.MultipleValidationErrors, WDL.Error.SyntaxError, WDL.Error.ValidationError) as e:
        errors = e.exceptions if isinstance(e, WDL.Error.MultipleValidationErrors) else [e]
        error_messages = [f"Error {i + 1} at line={error.pos.line} and column={error.pos.column}:\n{error}" for i, error in enumerate(errors)]
        raise ValueError(f"Unable to load {wdl_file_path} due to the following errors:\n{'\n'.join(error_messages)}") from e

    return convert(doc)


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
            if "vidarr_label" in output_metadata:
                print("Warning: There is a label inside output_meta that is being overriden by the specified vidarr_type")
            return output_metadata["vidarr_type"]
        else:
            return _map_output(
                doc, output, output.type, True, doc.struct_typedefs)

    for wf_input in (doc.workflow.available_inputs or []):
        # `workflow.available_inputs` gets all inputs (workflow, task, import)
        # `but `workflow.parameter_meta` only gets workflow inputs.
        input_name = wf_input.name.split(".")
        meta = None
        if len(input_name) == 1:
            meta = doc.workflow.parameter_meta.get(wf_input.name)
        elif len(input_name) == 2:
            task_name, parameter_name = input_name[0], input_name[1]
            for task in doc.tasks:
                if task.name == task_name:
                    meta = task.parameter_meta.get(parameter_name)
                    break

        if meta and isinstance(meta, dict) and "vidarr_type" in meta:
            vidarr_type = meta["vidarr_type"]
        else:
            vidarr_type = _map_input(wf_input.value.type, structures)

        # Optional should be processed after retry because it should be okay to omit a retriable value and use a
        # singular default.
        if meta and isinstance(meta, dict) and meta.get("vidarr_retry", False):
            vidarr_type = {"is": "retry", "inner": vidarr_type}

        if wf_input.value.expr:
            vidarr_type = {"is": "optional", "inner": vidarr_type}

        workflow_inputs[doc.workflow.name + "." + wf_input.name] = vidarr_type

    output_meta = doc.workflow.meta.get("output_meta", {})

    wdl_doc = doc.source_lines
    add_empty_optional_pair_for_vidarr_labels = False
    # Iterate over each output defined in the workflow
    for output in doc.workflow.outputs:

        # Check if the output name exists in the output metadata
        if output.name in output_meta:
            output_metadata = output_meta[output.name]

            if isinstance(output_metadata, dict) and 'vidarr_label' in output_metadata:
                vidarr_label = output_metadata['vidarr_label']

                source_line = output.pos.line - 1
                start_position = output.pos.column - 1
                end_position = output.pos.end_column - 1

                if isinstance(output.type, WDL.Type.File) and not output.type.optional:
                    output_line = (f'Pair[File, Map[String, String]] {output.name} = '
                                   f'({output.expr}, {{"vidarr_label": "{vidarr_label}"}})')
                elif isinstance(output.type, WDL.Type.File) and output.type.optional:
                    # Here we need to convert File? to Pair[File, Map[String,String]]?, but the WDL workflow that we are working
                    # with does not have a Pair[File, Map[String,String]]? to reference, and nor does Cromwell (WDL 1.0) support
                    # "None". So we create/inject an empty_optional_pair (see add_empty_optional_pair_for_vidarr_labels block) and
                    # reference this if the output file we're considering is not defined (optional) and we need to return an
                    # empty optional Pair[...]?.
                    # In the future if Cromwell supports WDL 1.2, this can be updated to:
                    # Pair[File, Map[String,String]]? maybeOutputPair =
                    #   if defined(maybeOutputFile) ( select_first([maybeOutputFile]), {"vidarr_label", vidarr_label_value} )
                    #   else None
                    # and the add_empty_optional_pair_for_vidarr_labels block removed.
                    add_empty_optional_pair_for_vidarr_labels = True
                    output_line = (f'Pair[File, Map[String,String]]? {output.name} = '
                                   f'if defined({output.expr}) then '
                                   f'(select_first([{output.expr}]), {{"vidarr_label": "{vidarr_label}"}}) '
                                   f'else empty_optional_pair')
                else:
                    raise ValueError(f"vidarr_label does not support {output.type}")

                wdl_doc[source_line] = wdl_doc[source_line][:start_position] + output_line + wdl_doc[source_line][end_position + 1:]

    if add_empty_optional_pair_for_vidarr_labels:
        workflow_section_end_position = doc.workflow.pos.end_line - 1
        # if(...) Pair[...] empty_optional_pair results in the type for empty_optional_pair being updated to Pair[...]?
        # see https://github.com/openwdl/wdl/blob/legacy/versions/1.0/SPEC.md#conditionals for more details
        output_line = f'if (false) {{ Pair[File, Map[String,String]] empty_optional_pair = ("",{{}}) }}'
        wdl_doc.insert(workflow_section_end_position, output_line)

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
        'workflow': '\n'.join(wdl_doc),
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
