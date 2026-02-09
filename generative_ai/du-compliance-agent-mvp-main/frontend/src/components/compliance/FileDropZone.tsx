import { useCallback, useState, useEffect } from 'react';
import { MdCloudUpload, MdClose, MdFolderOpen, MdAdd, MdUpload, MdEdit, MdCheck } from 'react-icons/md';
import { 
  BsFiletypePdf,
  BsFiletypeDoc,
  BsFiletypeDocx,
  BsFiletypeTxt,
  BsFiletypeMd,
  BsFiletypePptx,
  BsFiletypeXlsx,
  BsFiletypeCsv,
  BsFileEarmark
} from 'react-icons/bs';
import { getUrl } from '../../utils/urlUtils';

interface Regulation {
  filename: string;
  displayName: string;
}

interface UserUploadedPolicy {
  file: File;
  id: string; // Unique identifier for the uploaded policy
  customName?: string; // Optional custom name for the policy
}

interface FileDropZoneProps {
  onFilesSelected: (files: File[], selectedRegulations: string[], userUploadedPolicies: File[], policyCustomNames: Record<string, string>) => void;
}

export function FileDropZone({ onFilesSelected }: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [regulations, setRegulations] = useState<Regulation[]>([]);
  const [selectedRegulations, setSelectedRegulations] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(true);
  const [isLoadingRegulations, setIsLoadingRegulations] = useState(true);
  const [userUploadedPolicies, setUserUploadedPolicies] = useState<UserUploadedPolicy[]>([]);
  const [isPolicyModalOpen, setIsPolicyModalOpen] = useState(false);
  const [isPolicyDragging, setIsPolicyDragging] = useState(false);
  const [policyFilesToAdd, setPolicyFilesToAdd] = useState<File[]>([]);
  const [editingPolicyId, setEditingPolicyId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<string>('');
  const [duplicateNameError, setDuplicateNameError] = useState<string | null>(null);

  // Fetch regulations on mount
  useEffect(() => {
    const fetchRegulations = async () => {
      try {
        const response = await fetch(getUrl('/api/compliance/regulations'));
        if (response.ok) {
          const data = await response.json() as { regulations: Regulation[] };
          const regulationsList = data.regulations || [];
          setRegulations(regulationsList);
          // Default all regulations to selected
          const allFilenames = new Set<string>(regulationsList.map((r: Regulation) => r.filename));
          setSelectedRegulations(allFilenames);
          setSelectAll(true);
        }
      } catch (error) {
        console.error('Error fetching regulations:', error);
      } finally {
        setIsLoadingRegulations(false);
      }
    };
    fetchRegulations();
  }, []);

  // Handle select all checkbox
  const handleSelectAll = useCallback((checked: boolean) => {
    setSelectAll(checked);
    if (checked) {
      const allFilenames = new Set(regulations.map(r => r.filename));
      // Also select all user-uploaded policies
      userUploadedPolicies.forEach(policy => {
        allFilenames.add(policy.id);
      });
      setSelectedRegulations(allFilenames);
    } else {
      setSelectedRegulations(new Set());
    }
  }, [regulations, userUploadedPolicies]);

  // Handle individual regulation checkbox
  const handleRegulationToggle = useCallback((filename: string, checked: boolean) => {
    setSelectedRegulations(prev => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(filename);
      } else {
        newSet.delete(filename);
      }
      // Update select all state based on current selection
      const totalPolicies = regulations.length + userUploadedPolicies.length;
      setSelectAll(newSet.size === totalPolicies);
      return newSet;
    });
  }, [regulations.length, userUploadedPolicies.length]);

  // Update select all when regulations change
  useEffect(() => {
    const totalPolicies = regulations.length + userUploadedPolicies.length;
    if (totalPolicies > 0) {
      setSelectAll(selectedRegulations.size === totalPolicies);
    }
  }, [selectedRegulations.size, regulations.length, userUploadedPolicies.length]);

  // Handle ESC key to close policy modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isPolicyModalOpen) {
        setIsPolicyModalOpen(false);
        setPolicyFilesToAdd([]);
      }
    };

    if (isPolicyModalOpen) {
      window.addEventListener('keydown', handleEscape);
    }

    return () => {
      window.removeEventListener('keydown', handleEscape);
    };
  }, [isPolicyModalOpen]);

  const getFileIcon = useCallback((file: File) => {
    const name = file.name.toLowerCase();
    if (name.endsWith('.pdf') || file.type === 'application/pdf') return <BsFiletypePdf className="w-5 h-5 text-red-500" />;
    if (name.endsWith('.docx') || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') return <BsFiletypeDocx className="w-5 h-5 text-blue-600" />;
    if (name.endsWith('.doc') || file.type === 'application/msword') return <BsFiletypeDoc className="w-5 h-5 text-blue-600" />;
    if (name.endsWith('.txt') || file.type === 'text/plain') return <BsFiletypeTxt className="w-5 h-5 text-gray-600" />;
    if (name.endsWith('.md') || file.type === 'text/markdown') return <BsFiletypeMd className="w-5 h-5 text-purple-600" />;
    if (name.endsWith('.pptx') || file.type === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') return <BsFiletypePptx className="w-5 h-5 text-orange-500" />;
    if (name.endsWith('.xlsx') || name.endsWith('.xls') || name.endsWith('.xlsm') || file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || file.type === 'application/vnd.ms-excel') return <BsFiletypeXlsx className="w-5 h-5 text-green-600" />;
    if (name.endsWith('.csv') || file.type === 'text/csv') return <BsFiletypeCsv className="w-5 h-5 text-green-600" />;
    return <BsFileEarmark className="w-5 h-5 text-gray-500" />;
  }, []);

  const isSupportedFile = useCallback((file: File) => {
    const supportedMimeTypes = new Set([
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
      'application/msword', // .doc
      'text/plain', // .txt
      'text/markdown', // .md (some browsers may use text/plain)
      'application/vnd.openxmlformats-officedocument.presentationml.presentation', // .pptx
      'text/csv', // .csv
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
      'application/vnd.ms-excel', // .xls
      'application/vnd.ms-excel.sheet.macroEnabled.12' // .xlsm
    ]);

    if (file.type && supportedMimeTypes.has(file.type)) return true;

    const name = file.name.toLowerCase();
    return (
      name.endsWith('.pdf') ||
      name.endsWith('.docx') ||
      name.endsWith('.doc') ||
      name.endsWith('.txt') ||
      name.endsWith('.md') ||
      name.endsWith('.pptx') ||
      name.endsWith('.csv') ||
      name.endsWith('.xlsx') ||
      name.endsWith('.xls') ||
      name.endsWith('.xlsm')
    );
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const addFiles = useCallback((filesToAdd: File[]) => {
    setSelectedFiles(prev => {
      const existingNames = new Set(prev.map(file => file.name.toLowerCase()));
      const uniqueFiles = filesToAdd.filter(file => {
        const name = file.name.toLowerCase();
        if (existingNames.has(name)) {
          return false;
        }
        existingNames.add(name);
        return true;
      });
      if (uniqueFiles.length === 0) {
        return prev;
      }
      return [...prev, ...uniqueFiles];
    });
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files).filter(isSupportedFile);

    if (files.length > 0) {
      addFiles(files);
    }
  }, [addFiles, isSupportedFile]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files).filter(isSupportedFile) : [];
    if (files.length > 0) {
      addFiles(files);
    }
  }, [addFiles, isSupportedFile]);

  const handleUpload = useCallback(() => {
    if (selectedFiles.length > 0 && selectedRegulations.size > 0) {
      const selectedRegulationsArray = Array.from(selectedRegulations);
      // Filter to only include knowledge-base regulations (not user-uploaded policy IDs)
      const knowledgeBaseRegulations = selectedRegulationsArray.filter(reg => 
        regulations.some(r => r.filename === reg)
      );
      // Get user-uploaded policy files that are selected
      const selectedUserPolicies = userUploadedPolicies
        .filter(policy => selectedRegulations.has(policy.id))
        .map(policy => policy.file);
      // Build custom names mapping: policy ID -> custom name (or original filename if no custom name)
      const policyCustomNames: Record<string, string> = {};
      userUploadedPolicies
        .filter(policy => selectedRegulations.has(policy.id))
        .forEach(policy => {
          // Use the policy ID as the key, and the custom name or original filename as the value
          // The backend will match using the original filename from the File object
          policyCustomNames[policy.file.name] = policy.customName || policy.file.name;
        });
      onFilesSelected(selectedFiles, knowledgeBaseRegulations, selectedUserPolicies, policyCustomNames);
    }
  }, [selectedFiles, selectedRegulations, onFilesSelected, regulations, userUploadedPolicies]);

  const handleRemoveFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  // Policy upload handlers
  const handlePolicyDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsPolicyDragging(true);
  }, []);

  const handlePolicyDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsPolicyDragging(false);
  }, []);

  const handlePolicyDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsPolicyDragging(false);

    const files = Array.from(e.dataTransfer.files).filter(isSupportedFile);
    if (files.length > 0) {
      setPolicyFilesToAdd(prev => {
        const existingNames = new Set(prev.map(file => file.name.toLowerCase()));
        const uniqueFiles = files.filter(file => {
          const name = file.name.toLowerCase();
          if (existingNames.has(name)) {
            return false;
          }
          existingNames.add(name);
          return true;
        });
        return [...prev, ...uniqueFiles];
      });
    }
  }, [isSupportedFile]);

  const handlePolicyFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files).filter(isSupportedFile) : [];
    if (files.length > 0) {
      setPolicyFilesToAdd(prev => {
        const existingNames = new Set(prev.map(file => file.name.toLowerCase()));
        const uniqueFiles = files.filter(file => {
          const name = file.name.toLowerCase();
          if (existingNames.has(name)) {
            return false;
          }
          existingNames.add(name);
          return true;
        });
        return [...prev, ...uniqueFiles];
      });
    }
    // Reset input
    e.target.value = '';
  }, [isSupportedFile]);

  const handleAddPolicyFiles = useCallback(() => {
    if (policyFilesToAdd.length > 0) {
      const newPolicies: UserUploadedPolicy[] = policyFilesToAdd.map(file => ({
        file,
        id: `user_policy_${Date.now()}_${Math.random().toString(36).substr(2, 9)}_${file.name}`
      }));
      
      // Compute uniquePolicies before state updates to use for auto-selection
      setUserUploadedPolicies(prev => {
        const existingNames = new Set(prev.map(p => p.file.name.toLowerCase()));
        const uniquePolicies = newPolicies.filter(p => 
          !existingNames.has(p.file.name.toLowerCase())
        );
        
        // Auto-select newly added policies (only the ones that were actually added)
        setSelectedRegulations(prevRegs => {
          const newSet = new Set(prevRegs);
          uniquePolicies.forEach(policy => {
            newSet.add(policy.id);
          });
          return newSet;
        });
        
        return [...prev, ...uniquePolicies];
      });
      
      setPolicyFilesToAdd([]);
      setIsPolicyModalOpen(false);
    }
  }, [policyFilesToAdd]);

  const handleRemovePolicyFile = useCallback((policyId: string) => {
    setUserUploadedPolicies(prev => prev.filter(p => p.id !== policyId));
    setSelectedRegulations(prev => {
      const newSet = new Set(prev);
      newSet.delete(policyId);
      return newSet;
    });
  }, []);

  const handlePolicyToggle = useCallback((policyId: string, checked: boolean) => {
    setSelectedRegulations(prev => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(policyId);
      } else {
        newSet.delete(policyId);
      }
      const totalPolicies = regulations.length + userUploadedPolicies.length;
      setSelectAll(newSet.size === totalPolicies);
      return newSet;
    });
  }, [regulations.length, userUploadedPolicies.length]);

  const getPolicyDisplayName = useCallback((filename: string) => {
    // Remove extension and format nicely
    const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');
    return nameWithoutExt.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }, []);

  const getPolicyName = useCallback((policy: UserUploadedPolicy) => {
    return policy.customName || getPolicyDisplayName(policy.file.name);
  }, [getPolicyDisplayName]);

  const handleStartEdit = useCallback((policyId: string) => {
    const policy = userUploadedPolicies.find(p => p.id === policyId);
    if (policy) {
      setEditingPolicyId(policyId);
      setEditingValue(getPolicyName(policy));
      setDuplicateNameError(null); // Clear any previous error
    }
  }, [userUploadedPolicies, getPolicyName]);

  const handleSaveEdit = useCallback((policyId: string) => {
    const trimmedValue = editingValue.trim();
    if (trimmedValue === '') {
      setDuplicateNameError('Policy name cannot be empty');
      return; // Don't save empty names
    }
    
    // Check for duplicate custom names (excluding the current policy being edited)
    // Check against both user-uploaded policies and built-in regulations
    const hasDuplicateInUserPolicies = userUploadedPolicies.some(
      policy => policy.id !== policyId && 
      (policy.customName || getPolicyDisplayName(policy.file.name)).toLowerCase() === trimmedValue.toLowerCase()
    );
    
    const hasDuplicateInRegulations = regulations.some(
      r => r.displayName.toLowerCase() === trimmedValue.toLowerCase()
    );
    
    if (hasDuplicateInUserPolicies || hasDuplicateInRegulations) {
      setDuplicateNameError('A policy with this name already exists');
      return;
    }
    
    setUserUploadedPolicies(prev => 
      prev.map(policy => 
        policy.id === policyId 
          ? { ...policy, customName: trimmedValue }
          : policy
      )
    );
    setEditingPolicyId(null);
    setEditingValue('');
    setDuplicateNameError(null);
  }, [editingValue, userUploadedPolicies, regulations, getPolicyDisplayName]);

  const handleCancelEdit = useCallback(() => {
    setEditingPolicyId(null);
    setEditingValue('');
    setDuplicateNameError(null);
  }, []);

  const handleEditKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>, policyId: string) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveEdit(policyId);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancelEdit();
    }
  }, [handleSaveEdit, handleCancelEdit]);

  const hasSelectedRegulations = selectedRegulations.size > 0;

  return (
    <div className="flex flex-col items-center flex-1 px-8 pt-4 pb-8">
      <div className="text-center mb-6">
        <h1 className="text-4xl font-extrabold text-gray-900 mb-3">
          Compliance Checker Agent
        </h1>
        <p className="text-gray-500 text-lg">
          Hello there! Upload your documents and I'll check them for compliance with the policies you choose.
        </p>
      </div>
      <div className="w-full max-w-6xl flex gap-6">
        {/* Regulation Selection Panel */}
        <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Choose Policies to Check Against</h2>
          {isLoadingRegulations ? (
            <p className="text-gray-500 text-sm">Loading regulations...</p>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 pb-2 border-b border-gray-200">
                <input
                  type="checkbox"
                  id="select-all"
                  checked={selectAll}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="w-4 h-4 accent-primary border-gray-300 rounded focus:ring-primary cursor-pointer"
                />
                <label htmlFor="select-all" className="text-sm font-medium text-gray-700 cursor-pointer">
                  Select All
                </label>
                {!hasSelectedRegulations && (
                  <p className="text-red-500 text-sm">Please select at least one policy to proceed</p>
                )}
                <span className={`ml-auto text-sm ${!hasSelectedRegulations ? 'text-red-500' : 'text-gray-500'}`}>
                  ({selectedRegulations.size}/{regulations.length + userUploadedPolicies.length})
                </span>
              </div>
              <div className="flex flex-col gap-2 max-h-96 overflow-y-auto">
                {regulations.map((regulation) => (
                  <div key={regulation.filename} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={`regulation-${regulation.filename}`}
                      checked={selectedRegulations.has(regulation.filename)}
                      onChange={(e) => handleRegulationToggle(regulation.filename, e.target.checked)}
                      className="w-4 h-4 accent-primary border-gray-300 rounded focus:ring-primary cursor-pointer"
                    />
                    <label
                      htmlFor={`regulation-${regulation.filename}`}
                      className="text-sm text-gray-700 cursor-pointer flex-1"
                    >
                      {regulation.displayName}
                    </label>
                  </div>
                ))}
                {userUploadedPolicies.map((policy) => (
                  <div key={policy.id} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={`policy-${policy.id}`}
                      checked={selectedRegulations.has(policy.id)}
                      onChange={(e) => handlePolicyToggle(policy.id, e.target.checked)}
                      className="w-4 h-4 accent-primary border-gray-300 rounded focus:ring-primary cursor-pointer"
                      disabled={editingPolicyId === policy.id}
                    />
                    {editingPolicyId === policy.id ? (
                      <div className="flex-1 flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={editingValue}
                            onChange={(e) => {
                              setEditingValue(e.target.value);
                              setDuplicateNameError(null); // Clear error when user types
                            }}
                            onKeyDown={(e) => handleEditKeyDown(e, policy.id)}
                            className={`flex-1 text-sm text-gray-700 border rounded px-2 py-1 focus:outline-none focus:ring-2 ${
                              duplicateNameError 
                                ? 'border-red-500 focus:ring-red-500' 
                                : 'border-gray-300 focus:ring-primary'
                            }`}
                            autoFocus
                          />
                          <button
                            onClick={() => handleSaveEdit(policy.id)}
                            className="text-gray-400 hover:text-green-600 transition-colors ml-2"
                            title="Save name"
                          >
                            <MdCheck className="w-4 h-4" />
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="text-gray-400 hover:text-red-500 transition-colors"
                            title="Cancel editing"
                          >
                            <MdClose className="w-4 h-4" />
                          </button>
                        </div>
                        {duplicateNameError && (
                          <p className="text-xs text-red-500">{duplicateNameError}</p>
                        )}
                      </div>
                    ) : (
                      <>
                        <label
                          htmlFor={`policy-${policy.id}`}
                          className="text-sm text-gray-700 cursor-pointer flex-1"
                        >
                          {getPolicyName(policy)}
                        </label>
                        <button
                          onClick={() => handleStartEdit(policy.id)}
                          className="text-gray-400 hover:text-blue-500 transition-colors ml-2"
                          title="Edit policy name"
                        >
                          <MdEdit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleRemovePolicyFile(policy.id)}
                          className="text-gray-400 hover:text-red-500 transition-colors"
                          title="Remove policy"
                        >
                          <MdClose className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                ))}
              </div>
              <button
                onClick={() => setIsPolicyModalOpen(true)}
                className="mt-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-md transition-colors flex items-center gap-2 justify-center"
              >
                <MdAdd className="w-4 h-4" />
                Add more policies
              </button>
            </div>
          )}
        </div>

        {/* File Drop Zone */}
        <div className="flex-1">
          <div
            className={`
              flex flex-col items-center justify-center
              w-full h-full min-h-[400px]
              border-2 border-dashed rounded-lg
              transition-colors
              ${isDragging 
                ? 'border-secondary bg-secondary/10' 
                : 'border-gray-300 bg-gray-50'
              }
              ${selectedFiles.length > 0 ? 'p-8' : 'p-16'}
            `}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
        {selectedFiles.length === 0 ? (
          <>
            <MdCloudUpload className="w-12 h-12 text-gray-400 mb-4" />
            <p className="text-gray-600 text-sm mb-2">
              Drop supported files here or click to browse
            </p>
            <p className="text-gray-400 text-xs">
              Supported: .pdf, .docx, .doc, .pptx, .txt, .md, .csv, .xlsx, .xls
            </p>
            <input
              type="file"
              accept=".pdf,.docx,.doc,.txt,.md,.pptx,.csv,.xlsx,.xls,.xlsm,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              multiple
              onChange={handleFileInput}
              className="hidden"
              id="file-input"
            />
            <label
              htmlFor="file-input"
              className="mt-4 px-4 py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 cursor-pointer transition-colors flex items-center gap-2 justify-center"
            >
              <MdFolderOpen className="w-4 h-4" />
              Select Files
            </label>
          </>
        ) : (
          <div className="w-full flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              {selectedFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-md"
                >
                  <div className="flex items-center gap-3">
                    {getFileIcon(file)}
                    <span className="text-sm text-gray-700">{file.name}</span>
                  </div>
                  <button
                    onClick={() => handleRemoveFile(index)}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <MdClose className="w-5 h-5" />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <label
                htmlFor="file-input"
                className="flex-1 px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50 cursor-pointer transition-colors flex items-center gap-2 justify-center"
              >
                <MdAdd className="w-4 h-4" />
                Add More Files
              </label>
              <button
                onClick={handleUpload}
                disabled={!hasSelectedRegulations}
                className={`flex-1 px-4 py-2 text-sm rounded-md transition-colors flex items-center gap-2 justify-center ${
                  hasSelectedRegulations
                    ? 'bg-primary text-white hover:bg-primary/90'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                <MdUpload className="w-5 h-5" />
                Upload & Verify
              </button>
            </div>
            <input
              type="file"
              accept=".pdf,.docx,.doc,.txt,.md,.pptx,.csv,.xlsx,.xls,.xlsm,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              multiple
              onChange={handleFileInput}
              className="hidden"
              id="file-input"
            />
          </div>
        )}
          </div>
        </div>
      </div>

      {/* Policy Upload Modal */}
      {isPolicyModalOpen && (
        <div 
          className="fixed inset-0 backdrop-blur-sm bg-gray-500/20 flex items-center justify-center z-50"
          onClick={() => {
            setIsPolicyModalOpen(false);
            setPolicyFilesToAdd([]);
          }}
        >
          <div 
            className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Upload Policy Files</h3>
              <button
                onClick={() => {
                  setIsPolicyModalOpen(false);
                  setPolicyFilesToAdd([]);
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <MdClose className="w-6 h-6" />
              </button>
            </div>
            
            <div
              className={`
                flex flex-col items-center justify-center
                w-full min-h-[300px]
                border-2 border-dashed rounded-lg
                transition-colors
                ${isPolicyDragging 
                  ? 'border-secondary bg-secondary/10' 
                  : 'border-gray-300 bg-gray-50'
                }
                ${policyFilesToAdd.length > 0 ? 'p-8' : 'p-16'}
              `}
              onDragOver={handlePolicyDragOver}
              onDragLeave={handlePolicyDragLeave}
              onDrop={handlePolicyDrop}
            >
              {policyFilesToAdd.length === 0 ? (
                <>
                  <MdCloudUpload className="w-12 h-12 text-gray-400 mb-4" />
                  <p className="text-gray-600 text-sm mb-2">
                    Drop supported files here or click to browse
                  </p>
                  <p className="text-gray-400 text-xs">
                    Supported: .pdf, .docx, .doc, .pptx, .txt, .md, .csv, .xlsx, .xls
                  </p>
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.md,.pptx,.csv,.xlsx,.xls,.xlsm,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                    multiple
                    onChange={handlePolicyFileInput}
                    className="hidden"
                    id="policy-file-input"
                  />
                  <label
                    htmlFor="policy-file-input"
                    className="mt-4 px-4 py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 cursor-pointer transition-colors flex items-center gap-2 justify-center"
                  >
                    <MdFolderOpen className="w-4 h-4" />
                    Select Files
                  </label>
                </>
              ) : (
                <div className="w-full flex flex-col gap-4">
                  <div className="flex flex-col gap-2">
                    {policyFilesToAdd.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-md"
                      >
                        <div className="flex items-center gap-3">
                          {getFileIcon(file)}
                          <span className="text-sm text-gray-700">{file.name}</span>
                        </div>
                        <button
                          onClick={() => setPolicyFilesToAdd(prev => prev.filter((_, i) => i !== index))}
                          className="text-gray-400 hover:text-gray-600 transition-colors"
                        >
                          <MdClose className="w-5 h-5" />
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-3">
                    <label
                      htmlFor="policy-file-input"
                      className="flex-1 px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50 cursor-pointer transition-colors flex items-center gap-2 justify-center"
                    >
                      <MdAdd className="w-4 h-4" />
                      Add More Files
                    </label>
                    <button
                      onClick={handleAddPolicyFiles}
                      className="flex-1 px-4 py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 transition-colors flex items-center gap-2 justify-center"
                    >
                      <MdUpload className="w-5 h-5" />
                      Add Policies
                    </button>
                  </div>
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.md,.pptx,.csv,.xlsx,.xls,.xlsm,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                    multiple
                    onChange={handlePolicyFileInput}
                    className="hidden"
                    id="policy-file-input"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
