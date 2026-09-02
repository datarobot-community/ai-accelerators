"""`scatter_add` without a hard dependency on ``torch_scatter``.

``torch_scatter`` ships compiled C++/CUDA extensions whose wheel must match the
exact torch build (and CUDA toolkit) of the environment. When it doesn't, the
import fails *at load time* of the shared object, e.g. on DataRobot Notebooks::

    OSError: Could not load this library:
        .../site-packages/torch_scatter/_scatter_cuda.so

That is an ``OSError``, not an ``ImportError``, so both have to be caught.

Fallbacks, in order:
1. ``torch_scatter.scatter_add`` — used when it imports cleanly.
2. ``torch_geometric.utils.scatter(..., reduce="sum")`` — PyG >= 2.3, numerically
   identical to (1).
3. A pure-torch ``Tensor.scatter_add_`` implementation — no extra deps at all.
"""

import torch


def _scatter_add_torch(src, index, dim=0, dim_size=None):
    """Pure-torch equivalent of ``torch_scatter.scatter_add``."""
    if dim < 0:
        dim = src.dim() + dim
    if dim_size is None:
        dim_size = int(index.max()) + 1 if index.numel() > 0 else 0

    size = list(src.shape)
    size[dim] = dim_size
    out = torch.zeros(size, dtype=src.dtype, device=src.device)

    view_shape = [1] * src.dim()
    view_shape[dim] = -1
    idx = index.view(view_shape).expand_as(src)
    return out.scatter_add_(dim, idx, src)


try:
    from torch_scatter import scatter_add  # noqa: F401 - fast path when usable
except (ImportError, OSError):  # broken/mismatched C++ extension counts as OSError
    try:
        from torch_geometric.utils import scatter as _pyg_scatter

        def scatter_add(src, index, dim=0, dim_size=None):
            return _pyg_scatter(src, index, dim=dim, dim_size=dim_size, reduce="sum")

    except ImportError:
        scatter_add = _scatter_add_torch
