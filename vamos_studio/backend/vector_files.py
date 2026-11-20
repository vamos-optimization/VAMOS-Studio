"""Reference vectors from a file, for NSGA-III and RVEA: one of VAMOS's or the user's own.

By default NSGA-III and RVEA build their reference vectors as a Das-Dennis lattice, as VAMOS does.
As in jMetal and Evolver, they can instead start from a weight vector file (VAMOS 1.5, #365):

- one of the files VAMOS ships, jMetal's `W<objectives>D_<vectors>.dat` (such as `W3D_100.dat`);
- the user's own file: one vector per line, its components separated by whitespace or commas.

With a file, the population is the number of vectors, as in VAMOS. A request records the choice
(`SolveRequest.reference_vectors`): the name of a packaged file, or the user's file with its
vectors, so that each run of a series is self-contained and can be replayed. VAMOS reads the
vectors itself (`read_weight_vectors`), checks them, and records their source and checksum.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any, Final

import numpy as np
from numpy.typing import NDArray
from vamos.engine.algorithm.components.weight_vectors import read_weight_vectors
from vamos.resources import weight_path

from vamos_studio.backend.upstream.vamos_bridge import VECTOR_FIELDS, weight_populations

PACKAGED: Final = "packaged"
USER_FILE: Final = "file"
# The file the worker writes the user's vectors to, in the run's directory, for VAMOS to read.
RUN_VECTORS_FILE: Final = "reference_vectors.dat"

Spec = dict[str, Any]


def takes_vectors(algorithm: str) -> bool:
    """Whether the studio lets `algorithm` start from a file of reference vectors."""
    return algorithm in VECTOR_FIELDS


def packaged_files(n_obj: int) -> list[str]:
    """The weight vector files VAMOS ships for `n_obj` objectives, smallest first."""
    return [f"W{n_obj}D_{size}.dat" for size in weight_populations(n_obj)]


def packaged(name: str) -> Spec:
    """The choice of one of VAMOS's files, by name (e.g. "W3D_100.dat")."""
    weight_path(name)  # raises ValueError if VAMOS does not ship it
    return {"source": PACKAGED, "file": name}


def uploaded(name: str, data: bytes, n_obj: int) -> Spec:
    """The choice of the user's own file, with its vectors.

    Args:
        name: The file's name, for the record.
        data: Its content: one vector per line, components separated by whitespace or commas.
        n_obj: The problem's number of objectives, which each vector must have.

    Raises:
        ValueError: If the file is not a list of weight vectors with `n_obj` components.
    """
    vectors = _parse(data.decode("utf-8", errors="replace"), n_obj)
    return {"source": USER_FILE, "file": name, "vectors": vectors.tolist()}


def vectors_of(spec: Spec, n_obj: int) -> NDArray[np.float64]:
    """The vectors a choice gives, as VAMOS reads them."""
    if spec["source"] == PACKAGED:
        return read_weight_vectors(str(weight_path(spec["file"])), n_obj)
    return np.asarray(spec["vectors"], dtype=float)


def count(spec: Spec) -> int:
    """How many vectors a choice gives: the run's population."""
    if spec["source"] == PACKAGED:
        return int(spec["file"].split("_", 1)[1].removesuffix(".dat"))
    return len(spec["vectors"])


def describe(spec: Spec) -> str:
    """A choice in a few words, e.g. "W3D_100.dat, shipped with VAMOS (100 vectors)"."""
    origin = "shipped with VAMOS" if spec["source"] == PACKAGED else "your file"
    return f"{spec['file']}, {origin} ({count(spec):,} vectors)"


def materialize(spec: Spec, directory: Path) -> str:
    """The path VAMOS reads the vectors from: VAMOS's file, or the user's vectors written out."""
    if spec["source"] == PACKAGED:
        return str(weight_path(spec["file"]))
    path = directory / RUN_VECTORS_FILE
    np.savetxt(path, np.asarray(spec["vectors"], dtype=float), fmt="%.17g")
    return str(path)


def _parse(text: str, n_obj: int) -> NDArray[np.float64]:
    rows = [line.replace(",", " ") for line in text.splitlines() if line.strip()]
    if not rows:
        raise ValueError("The file has no vectors.")
    try:
        vectors = np.loadtxt(io.StringIO("\n".join(rows)), ndmin=2)
    except ValueError as error:
        raise ValueError(f"The file is not a list of numbers: {error}") from error
    if vectors.shape[1] != n_obj:
        raise ValueError(
            f"Its vectors have {vectors.shape[1]} components; the problem has {n_obj} objectives."
        )
    path = _scratch(vectors)
    try:
        return read_weight_vectors(str(path), n_obj)  # VAMOS's own checks
    finally:
        path.unlink(missing_ok=True)


def _scratch(vectors: NDArray[np.float64]) -> Path:
    handle, name = tempfile.mkstemp(suffix=".dat")
    with open(handle, "w", encoding="utf-8") as stream:
        np.savetxt(stream, vectors, fmt="%.17g")
    return Path(name)
