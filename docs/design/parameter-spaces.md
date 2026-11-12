# Design: parameter spaces as grammars

- **Status:** draft, agreed direction (2026-11-12)
- **Applies to:** VAMOS-Studio (now, as a local prototype) and VAMOS-CONFIG (later, in VAMOS)
- **Upstream target:** `vamos.algorithms.parameter_space` and a `vamos.parameter-space` schema
  (see [UPSTREAM.md](../../UPSTREAM.md))

## 1. Purpose

A parameter space says how an algorithm can be configured. Two projects need one:

- **VAMOS-Studio** shows the parameters of an algorithm as a form. The form starts from the
  default configuration, lets the user change it, and turns the result into a configuration
  that VAMOS can run.
- **VAMOS-CONFIG** brings Evolver's automatic algorithm configuration (AAC) to VAMOS. Several
  tools search the space:
  - VAMOS's own evolutionary algorithms, used as meta-optimizers in the style of Evolver, with
    the derivation-tree encoding as the main encoding;
  - Optuna;
  - SMAC3 (and BOHB, through ConfigSpace);
  - irace.

This document defines one model for parameter spaces and configurations. Every tool above, and
the Studio, works from that model.

## 2. Decisions

1. **A parameter space is a strict grammar.** This is Evolver's model: a categorical parameter
   chooses between productions, one for each of its values; a production holds the parameters
   that its value activates; numeric and boolean parameters are terminals. Every parameter has
   exactly one place in the tree.
2. **A configuration is a derivation of that grammar**: a derivation tree. The tree is the main
   encoding for meta-optimization. The flat encoding (a vector in [0, 1]^D) is derived from the
   tree and kept as a secondary encoding, for continuous meta-optimizers such as SMPSO.
3. **The grammar is data, not code.** It serializes to YAML and JSON under a versioned schema.
   VAMOS ships its spaces as package resources, and users can load their own, such as reduced
   spaces.
4. **Every parameter has a default.** Together, the defaults form the default configuration.
   It must be the same configuration that `XConfig.default()` builds.
5. **One vocabulary.** A configuration uses names and values that turn into an algorithm
   configuration through a single function per algorithm, owned by VAMOS. There are no
   per-consumer aliases.
6. **Every other format is a view of the grammar:** ConfigSpace, Optuna, irace, the flat
   encoding and the Studio form. They are derived from it without losing information. Nothing
   is derived in the other direction.

## 3. The grammar document

### 3.1 Top level

```yaml
schema: vamos.parameter-space
schema_version: 1.0.0
name: nsgaii_real            # unique id of the space
algorithm: nsgaii            # a VAMOS algorithm id
encoding: real               # the problem encoding the space is for
description: NSGA-II for real-coded problems.
parameters:                  # ordered mapping: the children of the root
  ...
```

### 3.2 Parameter nodes

Every node has these fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `type` | yes | `categorical`, `real`, `int` or `boolean` |
| `default` | yes | Its default value. It must belong to the node's domain. |
| `description` | no | One sentence, shown by the Studio |
| `label` | no | A display name; defaults to the parameter's name |
| `role` | no | One of VAMOS's tuning roles: `structural`, `operator`, `operator_rate`, `population`, `adaptive` |

Numeric terminals (`real`, `int`) also have:

| Field | Required | Meaning |
| --- | --- | --- |
| `range` | yes | `[low, high]`, both ends included |
| `log` | no | Sample on a log scale (needs `low > 0`) |

Categorical nodes also have:

| Field | Required | Meaning |
| --- | --- | --- |
| `values` | yes | Either a list of scalars, for productions without children, or a mapping from each value to its production |
| `global_sub_parameters` | no | Parameters present whatever the value. They are children of the node, not of a production. |

A production is a mapping that may contain `conditional_parameters`: the parameters that this
value activates. A value that has a production must be a string. A value without a production
may be a string, a number or a boolean.

A `boolean` node is always a terminal. A choice that activates parameters is a `categorical`
node.

Here is part of a grammar:

```yaml
parameters:
  crossover:
    type: categorical
    role: operator
    default: sbx
    global_sub_parameters:
      crossover_prob: {type: real, range: [0.6, 1.0], default: 0.9, role: operator_rate}
    values:
      sbx:
        conditional_parameters:
          crossover_eta: {type: real, range: [5.0, 40.0], default: 20.0}
      blx_alpha:
        conditional_parameters:
          crossover_alpha: {type: real, range: [0.0, 1.0], default: 0.5}
      arithmetic: {}
  mutation:
    type: categorical
    role: operator
    default: polynomial
    global_sub_parameters:
      mutation_prob_factor:
        type: real
        range: [0.25, 3.0]
        default: 1.0
        description: The mutation probability is this factor divided by the number of variables.
    values:
      polynomial:
        conditional_parameters:
          polynomial_eta: {type: real, range: [5.0, 40.0], default: 20.0}
      linked_polynomial:
        conditional_parameters:
          linked_polynomial_eta: {type: real, range: [5.0, 40.0], default: 20.0}
  offspring_ratio:
    type: categorical
    role: population
    default: 1.0
    values: [0.25, 0.5, 0.75, 1.0]
```

### 3.3 Well-formedness rules

A validator must reject any space that breaks one of these rules. It runs on every space that
VAMOS ships and on every space a user loads.

| Rule | Statement |
| --- | --- |
| G1 | Parameter names are unique in the whole space, and match `^[a-z][a-z0-9_]*$` |
| G2 | Each parameter has exactly one parent, a production or a categorical node. The YAML nesting guarantees this. There are no condition expressions and no multi-parent activation. |
| G3 | `default` belongs to the domain: inside `range`, one of `values`, or a boolean |
| G4 | `range` has `low <= high`; `log: true` needs `low > 0`; an `int` range has integer ends |
| G5 | `values` is non-empty and has no duplicates; a value with a production is a string |
| G6 | `schema` and `schema_version` are known, and `algorithm` and `encoding` exist in VAMOS |
| G7 | The default configuration builds and equals `XConfig.default()` for the algorithm (see §6) |

When a parameter applies to some values of a categorical node but not all, **duplicate it** under
each of those productions, with its own name (as `polynomial_eta` and `linked_polynomial_eta`
above). Evolver does the same, for example with `sbxDistributionIndex`.

When a parameter applies to every value, make it one of the node's `global_sub_parameters`.
Placing operator rates under their operator keeps related genes together, so the subtree
crossover exchanges them as a unit.

### 3.4 Identity

The **hash of a space** is the SHA-256 of its canonical JSON form: UTF-8, insertion order
preserved (order is meaningful: it is the depth-first order of the tree) and no insignificant
whitespace. Configurations and run manifests refer to a space by `name`, `schema_version` and
`hash`.

## 4. Configurations

### 4.1 Model

A configuration is a **derivation tree**. Every categorical node has a value. Under it hang its
global sub-parameters and the conditional parameters of the chosen production. Terminals hold
their values. A configuration is valid when:

- it contains exactly the parameters that are active in its derivation;
- each value is in its parameter's domain.

### 4.2 Serializations

The grammar is strict (G1, G2), so the active parameters, listed by name in depth-first order,
determine the derivation tree. That listing is the canonical serialization:

```yaml
schema: vamos.parameter-configuration
schema_version: 1.0.0
space: {name: nsgaii_real, schema_version: 1.0.0, hash: "sha256:..."}
values:                      # active parameters only, depth-first order
  crossover: sbx
  crossover_prob: 0.9
  crossover_eta: 20.0
  mutation: polynomial
  mutation_prob_factor: 1.0
  polynomial_eta: 20.0
  offspring_ratio: 1.0
```

There are two derived forms:

- **Command-line string**, as in Evolver's `VAR_CONF.txt`:
  `--crossover sbx --crossover_prob 0.9 --crossover_eta 20.0 ...`. Use it for logs, tables and
  hand-offs.
- **Flat mapping**, which is the `values` mapping on its own. Optuna, SMAC3 and irace exchange
  this form.

Parsing any of the three forms rebuilds the tree and checks it against the grammar.

## 5. Views derived from the grammar

| Consumer | View | Derivation |
| --- | --- | --- |
| VAMOS meta-optimizers (main) | Derivation tree | The grammar itself. A random tree chooses a production at each categorical node and samples each terminal. The operators are subtree crossover (it swaps subtrees whose roots are the same parameter) and tree mutation (it changes one node of the configuration; a categorical node takes a different value and regrows its production). |
| VAMOS meta-optimizers (secondary) | Flat encoding | One gene in [0, 1] per parameter of the space, in depth-first order. Decoding walks the tree and reads only the genes of active parameters. A categorical gene maps to index `min(floor(u * k), k - 1)`. |
| SMAC3, BOHB | `ConfigurationSpace` | Each node becomes a hyperparameter with `default_value`. A conditional parameter gets `EqualsCondition(child, parent, value)`. A global sub-parameter of a node that is not at the root gets `InCondition(child, node, all_values)`, which makes it active exactly when the node is. |
| Optuna | Define-by-run | A depth-first walk calls `suggest_categorical`, `suggest_float` or `suggest_int` for each active node. The default configuration is enqueued as the first trial. |
| irace | Parameters file | One line per parameter. A conditional parameter's condition is `\| parent == "value"`; a global sub-parameter of a non-root node gets `\| node %in% c(all values)`. The default configuration goes in the initial configurations file. |
| VAMOS-Studio | Form | The tree itself. The form shows the active branch and starts from the default configuration. |

VAMOS already has translators from its current `ParamSpace` to ConfigSpace, Optuna and irace
(`vamos/engine/tuning/_model_backend_utils.py`, `_irace_space.py`). Rewriting them over the
grammar makes them simpler, because they no longer need to parse condition expressions.

## 6. From a configuration to a run

- Each algorithm has **one** function that turns a configuration into its VAMOS configuration
  object (`NSGAIIConfig`, `MOEADConfig`, ...), owned by VAMOS. `config_from_assignment` already
  plays this role.
- **Defaults agree (G7):** turning the default configuration into a VAMOS configuration gives
  the same result as `XConfig.default()`. A test checks this for every space.
- **Problem-dependent settings** are expressed relative to the problem and resolved when the
  configuration is built. A space does not know the problem. For example:
  - `mutation_prob_factor` gives `prob = factor / n_var`;
  - algorithms whose population follows from reference directions or weight vectors (NSGA-III,
    RVEA, and MOEA/D with three or more objectives) derive it from `n_obj`. Their spaces either
    have no free `pop_size` parameter, or document how it is rounded to a valid size.

## 7. Migrating VAMOS's current spaces

There are 42 spaces today: 9 algorithms × 5 encodings, with SMPSO only for `real` and `mixed`.
They are Python builders in `vamos/engine/tuning/racing/bridge_spaces_*.py`. A survey of all of
them (VAMOS 1.1.0) shows that most of the structure is already a grammar:

- there are 203 conditional blocks, all of the form `parent == value`;
- no parameter belongs to more than one block.

These are the changes needed:

| Id | Current state | Change | Scope |
| --- | --- | --- | --- |
| M1 | `use_external_archive` (boolean) has conditional children, and `archive_prune_policy` uses the expression `cfg['archive_unbounded'] == False` | Use one categorical node, `external_archive: none \| unbounded \| bounded`, with `archive_prune_policy` under `bounded` | 42 spaces |
| M2 | `mutation_eta` is shared by `pm`/`polynomial` and `linked_polynomial` through an `or` expression | Duplicate it as `polynomial_eta` and `linked_polynomial_eta` | 7 spaces |
| M3 | Some VAMOS defaults are not among the space's choices: `initializer`, `repair`, and the per-type operators of mixed spaces (`real_crossover`, `perm_mutation`, ...). The Studio shows them as "VAMOS default". | Add the default as a value (for example `auto`, as Evolver's `createInitialSolutions: default`), or make the default one of the existing values | 10 parameters |
| M4 | 40 distinct parameters (267 occurrences across spaces) have no VAMOS default, mostly the settings of non-default operators (`blxab_alpha`, `gaussian_sigma`, `pcx_sigma_eta`, ...). The Studio makes up a starting value (the middle of the range). | Declare a default for each one, taken from the operator's own default in VAMOS where it exists | 40 parameters |
| M5 | Operator rates such as `crossover_prob`, `mutation_prob_factor` and `mutation_eta` are top-level parameters | Make them global sub-parameters of their operator node, so they travel with it in a subtree crossover | Recommended |
| M6 | The vocabulary differs from the configuration objects (`polynomial` in the space against `pm` in `MOEADConfig`'s default) | Use a single name for each operator in VAMOS | Every algorithm |

### 7.1 First grammar: `nsgaii_real` (VAMOS 1.1.0)

The first grammar, `vamos_studio/backend/upstream/spaces/nsgaii_real.yaml`, applies M1–M5 to
VAMOS 1.1.0's `build_nsgaii_config_space()`. It has 35 parameters, 8 of them top-level and 13
active by default. What it showed:

- **M3 needs no new values here.** With the same seed, `initializer: random` and `repair: clip`
  give exactly the same front as VAMOS's automatic defaults, so they are the defaults. A test
  checks it on ZDT1 and ZDT4.
- **G7 has to compare runs, not dictionaries.** `NSGAIIConfig.default()` and the configuration
  built from the grammar's defaults are written differently but run identically. For example,
  `("pm", {"prob": 1/n})` is the same as `polynomial` with `mutation_prob_factor: 1.0`, and an
  implicit tournament size is the same as `selection_size: 2`. The test runs both with one seed
  and compares the fronts.
- **M4:** the operators' own default arguments in VAMOS give a default to every parameter except
  two, which are marked PROVISIONAL: `gaussian_sigma` (no default in VAMOS) and
  `scatter_base_size_factor` (VAMOS uses 0.25, which is not one of the choices).
- **Reference fronts.** VAMOS 1.1's ZDT reference fronts are inaccurate, so the studio measures
  fronts against jMetal 7.11's, the files Evolver uses (`vamos_studio/resources/`).
- **Defaults and ranges change between VAMOS versions.** In 1.1.0 the SBX probability defaults to
  1.0, whereas `main` uses 0.9, and `simplex_epsilon` ranges over [0.1, 1.0]. The pinned VAMOS
  series and the drift-detection tests (`tests/test_nsgaii_grammar.py`) catch such changes.

### 7.2 Parameters the studio applies itself

A grammar may hold parameters that VAMOS does not have, which the studio applies around the run.
The first is `archive_subset_selection`, under `external_archive = unbounded`: how the result is
chosen from an unbounded archive. Such parameters are listed in `STUDIO_ONLY_PARAMETERS`
(`vamos_bridge.py`), are left out of what is passed to VAMOS, and are excluded from the
drift-detection comparison with VAMOS's space. Each one is an upstream candidate (`UPSTREAM.md`).

## 8. Plan

- **VAMOS-Studio (now).** `vamos_studio/backend/upstream/parameter_space.py` implements the
  grammar model, the validator, YAML/JSON serialization and configurations.
  - It **builds** the grammars from VAMOS 1.1's current spaces and `XConfig.default()`. It applies
    M1 and M2 as an adapter, and maps the renamed parameters back when it calls
    `config_from_assignment`.
  - For M3 and M4 it records the defaults it uses, and marks each one as provisional.
  - The Studio's forms and its run requests use only this model.
  - A drift-detection test keeps a snapshot of the generated grammars.
- **VAMOS-CONFIG (later, in VAMOS).**
  - The grammar becomes the source of truth: either the YAML files are shipped, or the builders
    output grammars.
  - M1 to M6 are applied in VAMOS itself.
  - The tuning back ends (ConfigSpace, Optuna, irace) are rewritten over the grammar.
  - A **derivation-tree solution type** is added, with its operators, so that VAMOS's
    evolutionary algorithms can be tree meta-optimizers. This needs its own design: VAMOS's
    encodings (`real`, `binary`, `integer`, `permutation`, `mixed`) are part of its stable
    contract.
  - The Studio then deletes its local version and raises its VAMOS pin.

## 9. Open questions

1. **Importing Evolver's spaces.** Should VAMOS-CONFIG read Evolver's YAML spaces? The structure
   matches, but operator names and sets differ (`SBX` against `sbx`, `UNDC` against `undx`), so
   it needs a mapping table. The benefit is comparing both frameworks on the same space.
2. **Forbidden combinations.** ConfigSpace and irace support constraints between parameters.
   They are left out of schema 1.0.0 until a real space needs one.
3. **Legal domain versus tuning range.** `range` is the range searched by tuning, and the Studio
   allows edits only inside it. A wider `limits` field for manual editing could be added if users
   need values outside the tuning range.
4. **Population size.** Decide whether `pop_size` belongs in the grammar of every algorithm, or
   is a run setting outside the space, as the Studio treats it today.
