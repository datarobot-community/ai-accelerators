import { useState, useCallback, useEffect } from 'react';
import { MdClose, MdEdit, MdCheck, MdWarning, MdDelete } from 'react-icons/md';
import { type CustomColumn } from '../../types/compliance';

interface ColumnManagerProps {
  columns: CustomColumn[];
  onChange: (columns: CustomColumn[]) => void;
  readOnly?: boolean;
}

interface ValidationError {
  columnIndex: number;
  field: 'name' | 'description';
  message: string;
}

/**
 * Sanitize a column name (preview what backend will do)
 */
function sanitizeColumnName(name: string): string {
  if (!name) return '';
  let sanitized = name.trim();
  sanitized = sanitized.replace(/ /g, '_');
  sanitized = sanitized.replace(/[^a-zA-Z0-9_\-]/g, '');
  sanitized = sanitized.toLowerCase();
  if (sanitized && !/^[a-zA-Z_]/.test(sanitized)) {
    sanitized = '_' + sanitized;
  }
  return sanitized;
}

/**
 * Validate column name
 */
function validateName(name: string): string | null {
  if (!name || !name.trim()) {
    return 'Column name cannot be empty';
  }
  const trimmed = name.trim();
  if (trimmed.length > 100) {
    return 'Column name must be at most 100 characters';
  }
  if (!/^[a-zA-Z0-9\s\-_]+$/.test(trimmed)) {
    return 'Column name can only contain letters, numbers, spaces, hyphens, and underscores';
  }
  return null;
}

/**
 * Validate description
 */
function validateDescription(description: string): string | null {
  if (!description || !description.trim()) {
    return 'Description cannot be empty';
  }
  const trimmed = description.trim();
  if (trimmed.length > 1000) {
    return 'Description must be at most 1000 characters. ' + (trimmed.length) + '/1000';
  }
  return null;
}

/**
 * Check for duplicate column names after sanitization
 */
function checkDuplicates(columns: CustomColumn[], currentIndex: number, currentName: string): string | null {
  const sanitized = sanitizeColumnName(currentName);
  if (!sanitized) return null;
  
  for (let i = 0; i < columns.length; i++) {
    if (i === currentIndex) continue;
    const otherSanitized = sanitizeColumnName(columns[i].name);
    if (otherSanitized === sanitized) {
      return `Duplicate column name: "${currentName}" will conflict with "${columns[i].name}" (both become "${sanitized}")`;
    }
  }
  return null;
}

export function ColumnManager({ columns, onChange, readOnly = false }: ColumnManagerProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [errors, setErrors] = useState<ValidationError[]>([]);
  // Track whether a save has been attempted for the current editing session
  const [saveAttempted, setSaveAttempted] = useState(false);

  // Validate all columns whenever they change (skip validation in read-only mode)
  useEffect(() => {
    if (readOnly) {
      // Don't validate default columns - they're system-defined
      setErrors([]);
      return;
    }
    
    const newErrors: ValidationError[] = [];
    columns.forEach((col, index) => {
      const nameError = validateName(col.name);
      if (nameError) {
        newErrors.push({ columnIndex: index, field: 'name', message: nameError });
      }
      const descError = validateDescription(col.description);
      if (descError) {
        newErrors.push({ columnIndex: index, field: 'description', message: descError });
      }
      const dupError = checkDuplicates(columns, index, col.name);
      if (dupError) {
        newErrors.push({ columnIndex: index, field: 'name', message: dupError });
      }
    });
    setErrors(newErrors);
  }, [columns, readOnly]);

  const getError = useCallback((index: number, field: 'name' | 'description'): string | null => {
    const error = errors.find(e => e.columnIndex === index && e.field === field);
    return error ? error.message : null;
  }, [errors]);

  // Check if there are any errors in non-editing columns
  const hasAnyError = errors.some(e => e.columnIndex !== editingIndex);

  // Auto-start editing when a new empty column is added
  useEffect(() => {
    if (!readOnly && columns.length > 0) {
      const lastColumn = columns[columns.length - 1];
      if (!lastColumn.name && !lastColumn.description && editingIndex === null) {
        // New empty column was added, start editing it
        setEditingIndex(columns.length - 1);
        setEditName('');
        setEditDescription('');
        setSaveAttempted(false);
      }
    }
  }, [columns.length, readOnly, editingIndex]);

  const handleRemoveColumn = useCallback((index: number) => {
    const newColumns = columns.filter((_, i) => i !== index);
    onChange(newColumns);
    if (editingIndex === index) {
      // If the removed column is the one being edited, cancel editing
      setEditingIndex(null);
      setEditName('');
      setEditDescription('');
    } else if (editingIndex !== null && index < editingIndex) {
      // If a column before the editing index was removed, adjust the index
      // to account for the array shift
      setEditingIndex(editingIndex - 1);
    }
  }, [columns, onChange, editingIndex]);

  const handleStartEdit = useCallback((index: number) => {
    setEditingIndex(index);
    setEditName(columns[index].name);
    setEditDescription(columns[index].description);
    setSaveAttempted(false);
  }, [columns]);

  const handleSaveEdit = useCallback(() => {
    if (editingIndex === null) return;
    
    // Mark that save was attempted - this will trigger error display
    setSaveAttempted(true);
    
    // Validate before saving
    const nameError = validateName(editName);
    const descError = validateDescription(editDescription);
    const dupError = checkDuplicates(columns, editingIndex, editName);
    
    if (nameError || descError || dupError) {
      // Don't save if there are validation errors
      return;
    }
    
    const newColumns = [...columns];
    newColumns[editingIndex] = { 
      ...newColumns[editingIndex], 
      name: editName,
      description: editDescription
    };
    onChange(newColumns);
    setEditingIndex(null);
    setEditName('');
    setEditDescription('');
    setSaveAttempted(false);
  }, [editingIndex, editName, editDescription, columns, onChange]);

  const handleCancelEdit = useCallback(() => {
    // If this is a new column with no name, remove it
    if (editingIndex !== null && !columns[editingIndex].name && !columns[editingIndex].description) {
      const newColumns = columns.filter((_, i) => i !== editingIndex);
      onChange(newColumns);
    }
    setEditingIndex(null);
    setEditName('');
    setEditDescription('');
    setSaveAttempted(false);
  }, [editingIndex, columns, onChange]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      handleCancelEdit();
    }
  }, [handleCancelEdit]);

  return (
    <div className="flex flex-col gap-4">
      {hasAnyError && (
        <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
          <MdWarning className="w-5 h-5 flex-shrink-0" />
          <span>Please fix the validation errors below before proceeding.</span>
        </div>
      )}

      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Column Name</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Column Description</th>
              {!readOnly && (
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Actions</th>
              )}
            </tr>
          </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {columns.map((column, index) => {
                const isEditing = editingIndex === index;
                // For editing rows, compute errors based on current edit values (only if save was attempted)
                // For non-editing rows, use the stored errors
                const liveNameError = isEditing && saveAttempted ? (validateName(editName) || checkDuplicates(columns, index, editName)) : null;
                const liveDescError = isEditing && saveAttempted ? validateDescription(editDescription) : null;
                const storedNameError = !isEditing ? getError(index, 'name') : null;
                const storedDescError = !isEditing ? getError(index, 'description') : null;
                const nameError = isEditing ? liveNameError : storedNameError;
                const descError = isEditing ? liveDescError : storedDescError;

                return (
                  <tr 
                    key={index}
                    className={`hover:bg-gray-50 ${(nameError || descError) ? 'bg-red-50' : ''}`}
                  >
                    {/* Column Name Cell */}
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <div className="flex flex-col gap-1">
                          <input
                            type="text"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            onKeyDown={handleKeyDown}
                            className={`w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-2 ${
                              nameError 
                                ? 'border-red-300 focus:ring-red-500' 
                                : 'border-gray-300 focus:ring-primary'
                            }`}
                            placeholder="Column name"
                            autoFocus
                          />
                          {editName && (
                            <span className="text-xs text-gray-500">
                              Will become: <code className="bg-gray-200 px-1 rounded">{sanitizeColumnName(editName)}</code>
                            </span>
                          )}
                          {nameError && (
                            <p className="text-xs text-red-500">{nameError}</p>
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2">
                            <span className={`text-sm ${nameError ? 'text-red-600' : 'text-gray-900'}`}>
                              {column.name || <span className="italic text-gray-400">Unnamed column</span>}
                            </span>
                            {column.isDefault && (
                              <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                                Default
                              </span>
                            )}
                          </div>
                          {nameError && (
                            <p className="text-xs text-red-500">{nameError}</p>
                          )}
                        </div>
                      )}
                    </td>

                    {/* Column Description Cell */}
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <div className="flex flex-col gap-1">
                          <textarea
                            value={editDescription}
                            onChange={(e) => setEditDescription(e.target.value)}
                            onKeyDown={handleKeyDown}
                            className={`w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-2 resize-none ${
                              descError 
                                ? 'border-red-300 focus:ring-red-500' 
                                : 'border-gray-300 focus:ring-primary'
                            }`}
                            placeholder="Description"
                            rows={2}
                          />
                          <span className="text-xs text-gray-500">
                            {editDescription.length}/1000 characters
                          </span>
                          {descError && (
                            <p className="text-xs text-red-500">{descError}</p>
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-col gap-1">
                          <p className={`text-sm ${descError ? 'text-red-600' : 'text-gray-600'}`}>
                            {column.description || <span className="italic text-gray-400">No description</span>}
                          </p>
                          {descError && (
                            <p className="text-xs text-red-500">{descError}</p>
                          )}
                        </div>
                      )}
                    </td>

                    {/* Actions Cell */}
                    {!readOnly && (
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          {isEditing ? (
                            <>
                              <button
                                onClick={handleSaveEdit}
                                className="p-1 text-gray-500 hover:text-green-600 transition-colors"
                                title="Save"
                              >
                                <MdCheck className="w-5 h-5" />
                              </button>
                              <button
                                onClick={handleCancelEdit}
                                className="p-1 text-gray-500 hover:text-red-500 transition-colors"
                                title="Cancel"
                              >
                                <MdClose className="w-5 h-5" />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => handleStartEdit(index)}
                                className="p-1 text-gray-400 hover:text-blue-500 transition-colors"
                                title="Edit column"
                              >
                                <MdEdit className="w-5 h-5" />
                              </button>
                              <button
                                onClick={() => handleRemoveColumn(index)}
                                className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                                title="Remove column"
                              >
                                <MdDelete className="w-5 h-5" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
      </div>

      {columns.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No columns defined. Add at least one column to proceed.</p>
        </div>
      )}
    </div>
  );
}

export { validateName, validateDescription, checkDuplicates };

