import math

from rdkit import Chem
import torch
from torch_geometric.data import Data

# Width of the per-bond feature vector built in smiles_to_graph. Needed to shape
# an empty edge_attr for molecules that have no bonds at all (a single atom, e.g.
# "C" or "[Na+]"), where the bond loop never runs and there is no sample vector
# to measure. Keep in step with the `bond_feat` list below.
BOND_FEATURE_DIM = 21

# Shortest-path distances are >= 0. The previous sentinel (10.0) collided with a
# real 10-bond path, so "no * in this fragment" looked identical to "ten bonds
# from *". Negative is reserved for missing.
NO_ATTACHMENT_PATH = -1.0


def is_carbonyl_carbon(atom, mol):
    """Carbonyl carbon: C=O"""
    if atom.GetAtomicNum() != 6:
        return False
    for neighbor in atom.GetNeighbors():
        if neighbor.GetAtomicNum() == 8:
            bond = mol.GetBondBetweenAtoms(atom.GetIdx(), neighbor.GetIdx())
            if bond.GetBondType() == Chem.rdchem.BondType.DOUBLE:
                return True
    return False


def is_carboxyl_carbon(atom, mol):
    """Carboxyl carbon: C(=O)OH"""
    if not is_carbonyl_carbon(atom, mol):
        return False
    oh_count = 0
    for neighbor in atom.GetNeighbors():
        # MolFromSmiles leaves hydrogens implicit, so looking for an explicit
        # H *atom* among the oxygen's neighbours never matches. Ask the
        # oxygen how many hydrogens it carries instead.
        if neighbor.GetAtomicNum() == 8 and neighbor.GetTotalNumHs(includeNeighbors=True) > 0:
            oh_count += 1
    return oh_count > 0


def _get_attachment_distance(atom, mol):
    """Shortest-path distance to the nearest attachment point (`*`).

    Returns 0.0 when this atom *is* an attachment point, and
    ``NO_ATTACHMENT_PATH`` (-1) when there is no `*` or no path to one
    (a disconnected fragment in a '.'-separated SMILES).
    """
    try:
        if atom.GetAtomicNum() == 0:
            return 0.0

        attachment_atoms = [a for a in mol.GetAtoms() if a.GetAtomicNum() == 0]
        if not attachment_atoms:
            return NO_ATTACHMENT_PATH

        min_distance = float("inf")
        for attachment in attachment_atoms:
            try:
                distance = Chem.rdmolops.GetShortestPath(mol, atom.GetIdx(), attachment.GetIdx())
                # GetShortestPath returns an EMPTY tuple (not None) when the two
                # atoms live in disconnected fragments. Treat empty / degenerate
                # paths as "no path" so the -1 sentinel applies.
                if distance:
                    path_length = len(distance) - 1
                    if 0 <= path_length < min_distance:
                        min_distance = path_length
            except Exception:
                try:
                    visited = set()
                    queue = [(atom.GetIdx(), 0)]
                    visited.add(atom.GetIdx())
                    while queue:
                        current_idx, dist = queue.pop(0)
                        if current_idx == attachment.GetIdx():
                            if dist < min_distance:
                                min_distance = dist
                            break
                        current_atom = mol.GetAtomWithIdx(current_idx)
                        for neighbor in current_atom.GetNeighbors():
                            neighbor_idx = neighbor.GetIdx()
                            if neighbor_idx not in visited:
                                visited.add(neighbor_idx)
                                queue.append((neighbor_idx, dist + 1))
                except Exception:
                    continue

        return float(min_distance) if min_distance != float("inf") else NO_ATTACHMENT_PATH
    except Exception:
        return NO_ATTACHMENT_PATH


def _is_potential_crosslink_bond(atom1, atom2, mol):
    """Check if this bond could be involved in polymer crosslinking"""
    try:
        aromatic_bond = atom1.GetIsAromatic() or atom2.GetIsAromatic()
        high_degree = atom1.GetTotalDegree() > 3 or atom2.GetTotalDegree() > 3
        heteroatom_bond = atom1.GetAtomicNum() not in [1, 6] or atom2.GetAtomicNum() not in [1, 6]
        return int(aromatic_bond or high_degree or heteroatom_bond)
    except:
        return 0


def _has_attachment_neighbor(atom, mol):
    """Check if atom has an attachment point (*) as a neighbor"""
    try:
        for neighbor in atom.GetNeighbors():
            if neighbor.GetAtomicNum() == 0:
                return True
        return False
    except:
        return False


def smiles_to_graph(smiles_str, atom_map, y_val=None):
    """
    Converts a SMILES string into a PyTorch Geometric Data object.
    Returns a zero-filled graph if the SMILES cannot be featurized.

    An unusable *target*, by contrast, raises: a bad label is a data error,
    not a molecule to be tolerated. Fabricating 0.0 for an unparseable value
    (e.g. a censored ``<0.05``) hides it inside the real Tc range, and
    letting NaN through NaNs every weight on the first batch and only
    surfaces much later as a sklearn "Input contains NaN" error.
    """
    y_float = None
    if y_val is not None:
        try:
            y_float = float(y_val)
        except (TypeError, ValueError):
            raise ValueError(f"Target for SMILES {smiles_str!r} is not numeric: {y_val!r}")
        if not math.isfinite(y_float):
            raise ValueError(f"Target for SMILES {smiles_str!r} is not finite: {y_val!r}")

    def create_zero_graph():
        x = torch.zeros((1, len(atom_map) + 12), dtype=torch.float)
        edge_index = torch.empty((2, 0), dtype=torch.long)
        edge_attr = torch.empty((0, BOND_FEATURE_DIM), dtype=torch.float)
        if y_float is not None:
            y_tensor = torch.tensor([[y_float]], dtype=torch.float)
            return Data(
                x=x, edge_index=edge_index, edge_attr=edge_attr, y=y_tensor, smiles=str(smiles_str)
            )
        else:
            return Data(x=x, edge_index=edge_index, edge_attr=edge_attr, smiles=str(smiles_str))

    try:
        if not isinstance(smiles_str, str) or not smiles_str.strip():
            return create_zero_graph()
        if not isinstance(atom_map, dict) or not atom_map:
            return create_zero_graph()

        mol = Chem.MolFromSmiles(smiles_str)
        if mol is None or mol.GetNumAtoms() == 0:
            return create_zero_graph()

        # Node Features
        node_features = []
        for atom in mol.GetAtoms():
            try:
                symbol = atom.GetSymbol()
                features = [0] * len(atom_map)
                if symbol in atom_map:
                    features[atom_map[symbol]] = 1
                features.extend(
                    [
                        atom.GetAtomicNum(),
                        atom.GetTotalDegree(),
                        atom.GetFormalCharge(),
                        atom.GetTotalNumHs(includeNeighbors=True),
                        atom.GetNumRadicalElectrons(),
                        int(atom.GetIsAromatic()),
                        int(atom.IsInRing()),
                        int(atom.GetHybridization() == Chem.rdchem.HybridizationType.SP),
                        int(atom.GetHybridization() == Chem.rdchem.HybridizationType.SP2),
                        int(atom.GetHybridization() == Chem.rdchem.HybridizationType.SP3),
                        int(atom.GetHybridization() == Chem.rdchem.HybridizationType.S),
                        int(atom.GetHybridization() == Chem.rdchem.HybridizationType.UNSPECIFIED),
                    ]
                )
                node_features.append(features)
            except:
                return create_zero_graph()

        if not node_features:
            return create_zero_graph()

        try:
            x = torch.tensor(node_features, dtype=torch.float)
        except:
            return create_zero_graph()

        # Edge Index and Features
        edge_indices, edge_attrs = [], []
        try:
            for bond in mol.GetBonds():
                i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
                if i >= mol.GetNumAtoms() or j >= mol.GetNumAtoms():
                    continue
                edge_indices.extend([(i, j), (j, i)])
                bt = bond.GetBondType()
                stereo = bond.GetStereo()
                atom1 = bond.GetBeginAtom()
                atom2 = bond.GetEndAtom()
                angles_1 = len([n for n in atom1.GetNeighbors() if n.GetIdx() != atom2.GetIdx()])
                angles_2 = len([n for n in atom2.GetNeighbors() if n.GetIdx() != atom1.GetIdx()])
                dist_1 = float(_get_attachment_distance(atom1, mol))
                dist_2 = float(_get_attachment_distance(atom2, mol))

                # Direction-independent part of the bond vector.
                shared_head = [
                    int(bt == Chem.rdchem.BondType.SINGLE),
                    int(bt == Chem.rdchem.BondType.DOUBLE),
                    int(bt == Chem.rdchem.BondType.TRIPLE),
                    int(bt == Chem.rdchem.BondType.AROMATIC),
                    int(bt == Chem.rdchem.BondType.DATIVE),
                    int(stereo == Chem.rdchem.BondStereo.STEREONONE),
                    int(stereo == Chem.rdchem.BondStereo.STEREOZ),
                    int(stereo == Chem.rdchem.BondStereo.STEREOE),
                    int(stereo == Chem.rdchem.BondStereo.STEREOCIS),
                    int(stereo == Chem.rdchem.BondStereo.STEREOTRANS),
                    int(stereo == Chem.rdchem.BondStereo.STEREOANY),
                    int(bond.IsInRing()),
                    int(bond.GetIsConjugated()),
                ]
                shared_mid = [
                    float(min(angles_1, angles_2)),
                    float(max(angles_1, angles_2)),
                ]
                shared_tail = [
                    int(_is_potential_crosslink_bond(atom1, atom2, mol)),
                    int(
                        _has_attachment_neighbor(atom1, mol) or _has_attachment_neighbor(atom2, mol)
                    ),
                ]

                # The four per-atom slots are keyed to RDKit's begin/end
                # assignment, which follows the order the atoms appear in the
                # input string. Emitting the same vector for both directed
                # copies therefore made slot meaning depend on how the SMILES
                # happened to be written, and left the model unable to tell
                # whether a slot describes the edge's source or destination.
                # Order them source-first per direction instead.
                edge_attrs.extend(
                    [
                        shared_head
                        + [float(angles_1), float(angles_2)]
                        + shared_mid
                        + [dist_1, dist_2]
                        + shared_tail,
                        shared_head
                        + [float(angles_2), float(angles_1)]
                        + shared_mid
                        + [dist_2, dist_1]
                        + shared_tail,
                    ]
                )
        except:
            edge_indices, edge_attrs = [], []

        try:
            if edge_indices:
                edge_index = torch.tensor(edge_indices, dtype=torch.long).t().contiguous()
                edge_attr = torch.tensor(edge_attrs, dtype=torch.float)
            else:
                edge_index = torch.empty((2, 0), dtype=torch.long)
                edge_attr = torch.empty((0, BOND_FEATURE_DIM), dtype=torch.float)
        except:
            return create_zero_graph()

        try:
            if y_float is not None:
                y_tensor = torch.tensor([[y_float]], dtype=torch.float)
                return Data(
                    x=x, edge_index=edge_index, edge_attr=edge_attr, y=y_tensor, smiles=smiles_str
                )
            else:
                return Data(x=x, edge_index=edge_index, edge_attr=edge_attr, smiles=smiles_str)
        except:
            return create_zero_graph()
    except:
        return create_zero_graph()
