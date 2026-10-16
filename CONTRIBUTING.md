# Contributing

Run the host tests before submitting changes. Kernel or rendering/input changes also require regenerated exact-ROM checks and reviewed evidence. A changed ROM hash is expected after code changes; explain it rather than updating golden hashes without investigation. `tools/reproduce.py` compares against the recorded source version, so update records only after new measurements.

Do not submit commercial binaries, assets, level packs, captures, generated IR/ROMs or local rights documents without independently established publication rights. Public failure reports should describe methods, hashes and outcomes without proprietary payloads. Included fixture evidence is publishable because those boards/code were authored for this repository under MIT.

For an adapter proposal, include an input/version boundary, rights/access requirements, deterministic parser tests, a behavioral contract, control analysis, predeclared acceptance/rejection criteria, a native invalidating experiment, and separate effort/fidelity/performance/transfer results. A magic signature, extracted image or compiled ROM alone is not a successful adaptation. Label observed/inferred/chosen/untested claims explicitly.
