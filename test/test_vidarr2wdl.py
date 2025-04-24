import json
import os

import pytest

import vidarr.wdl


def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


def compare_wdl(base_name: str) -> bool:
    golden_file = os.path.join(os.path.dirname(__file__), base_name + ".json")
    expected = ordered(json.load(open(golden_file)))
    wdl_file = os.path.join(os.path.dirname(__file__), base_name + ".wdl")
    actual = ordered(vidarr.wdl.parse(wdl_file))
    assert actual == expected


def tests_fastqc():
    compare_wdl("fastqc")


def tests_bcl2fastq():
    compare_wdl("bcl2fastq")


def tests_star():
    compare_wdl("star")


def tests_fingerprintCompare():
    compare_wdl("fingerprintCompare")


def tests_dnaSeqQc():
    compare_wdl("dnaSeqQC")


def tests_bmpp():
    compare_wdl("bamMergePreprocessing")


def tests_empty():
    compare_wdl("empty")


def tests_retry():
    compare_wdl("crosscheckFingerprints_retry")


def tests_bad():
    wdl_path = os.path.join(os.path.dirname(__file__), "bad.wdl")
    with pytest.raises(ValueError) as e:
        vidarr.wdl.parse(wdl_path)
    assert str(e.value) == f"Unable to load {wdl_path} due to the following errors:\nError 1 at line=13 and column=28:\nExpected Int instead of File"
