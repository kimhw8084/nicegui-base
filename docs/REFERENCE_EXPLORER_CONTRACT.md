# Reference Explorer contract

`nicegui_base.workbench.models.ReferenceContract` is the single typed contract for
catalog entries. `WorkbenchEntry.reference_contract` is derived from the canonical
registry projection; the registry remains the source of API truth.

Every entry exposes variants, connected configuration, use/avoid guidance, input
shape, lifecycle states, responsive and accessibility behavior, production guidance,
relationships, and AI selection metadata (`best_for`, `avoid_for`, `requires`,
`produces`, `alternatives`, `complements`, `domain_tags`, `complexity`, and `density`).
Visual entries declare a direct registered renderer and proof route. API, policy,
runtime, and construction entries declare an explicit nonvisual variant instead of a
blank or generic visual preview.

Reference Explorer search is deterministic and accepts `intent`, `data_shape`,
`domain`, and `related_to` filters in addition to name/tag/query matching:

```python
from nicegui_base.workbench import search

search('monitor equipment health', limit=10)
search('', intent='investigation', domain='semiconductor')
search('', data_shape='rows', related_to='analytics:fdc_recipe_step_trace')
```

Use `catalog_contract_audit()` in release and health checks. A catalog is complete
only when every entry validates and each visual/nonvisual example has explicit proof.
Examples are rendered by `catalog_runtime.render_catalog_example()` and the same
production wrappers used by generated applications; reference pages do not use
iframes or project-authoring state.
