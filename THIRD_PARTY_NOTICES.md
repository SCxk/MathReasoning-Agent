# Third-Party Resources

The application retains third-party mathematical strategy resources and
upstream descriptions from its source project.

- The original strategy index metadata names its base corpus
  `ReasonFlux-V2-Template`, with supplemental/translated method materials.
  The original resource directory's `license: apache-2.0` declaration is
  preserved in `strategyrag/README.md`.
- The optional encoder is
  [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).
  Its original model card, including the Apache-2.0 declaration and attribution,
  is preserved in `strategyrag/Qwen3-Embedding-0.6B/README.md`.
  Model weights and tokenizer/configuration bundles are not included.
- JavaScript and Python dependencies remain identified in their manifests and
  lockfile. Their packages and package-specific license texts are installed by
  the relevant package manager rather than bundled in this source copy.

No root project LICENSE was present in the source checkout. This release does
not assign a new license or claim ownership of third-party resources.
