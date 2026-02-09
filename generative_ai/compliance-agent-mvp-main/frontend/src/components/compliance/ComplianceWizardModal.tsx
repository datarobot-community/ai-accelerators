import { useState, useCallback, useEffect, useMemo } from 'react';
import { 
  MdClose, 
  MdChevronLeft, 
  MdChevronRight, 
  MdCloudUpload, 
  MdFolderOpen,
  MdAdd,
  MdEdit,
  MdCheck,
  MdUpload,
  MdDownload
} from 'react-icons/md';
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
import { type CustomColumn, type Regulation, type UserUploadedPolicy, type WizardData, type CustomPrompts } from '../../types/compliance';
import { ColumnManager, validateName, validateDescription, checkDuplicates } from './ColumnManager';
import { getUrl } from '../../utils/urlUtils';
import { saveCustomColumns, loadCustomColumns, saveCustomPrompts, loadCustomPrompts } from '../../utils/storageUtils';

interface ComplianceWizardModalProps {
  onComplete: (data: WizardData) => void;
  onCancel: () => void;
}

type WizardStep = 'files' | 'policies' | 'define-prompts' | 'define-columns';

const STEPS: WizardStep[] = ['files', 'policies', 'define-prompts', 'define-columns'];

const STEP_LABELS: Record<WizardStep, string> = {
  'files': 'Upload Files',
  'policies': 'Select Policies',
  'define-prompts': 'Define Prompts',
  'define-columns': 'Define Output'
};

// Fixed system prompt prefix that cannot be modified
const FIXED_SYSTEM_PREFIX = "You are a meticulous compliance analyst working at du (ETIC).";

export function ComplianceWizardModal({ onComplete, onCancel }: ComplianceWizardModalProps) {
  // Current step
  const [currentStep, setCurrentStep] = useState<WizardStep>('files');
  const currentStepIndex = STEPS.indexOf(currentStep);

  // Step 1: Files
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Step 2: Policies
  const [regulations, setRegulations] = useState<Regulation[]>([]);
  const [selectedRegulations, setSelectedRegulations] = useState<Set<string>>(new Set());
  const [selectAll, setSelectAll] = useState(true);
  const [isLoadingRegulations, setIsLoadingRegulations] = useState(true);
  const [userUploadedPolicies, setUserUploadedPolicies] = useState<UserUploadedPolicy[]>([]);
  const [isPolicyModalOpen, setIsPolicyModalOpen] = useState(false);
  const [isPolicyDragging, setIsPolicyDragging] = useState(false);
  const [policyFilesToAdd, setPolicyFilesToAdd] = useState<File[]>([]);
  const [editingPolicyId, setEditingPolicyId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [duplicateNameError, setDuplicateNameError] = useState<string | null>(null);

  // Step 3: Prompts
  const [defaultSystemPrompt, setDefaultSystemPrompt] = useState<string>('');
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [isLoadingPrompts, setIsLoadingPrompts] = useState(true);
  const [promptsUploadError, setPromptsUploadError] = useState<string | null>(null);

  // Step 4: Columns
  const [defaultColumns, setDefaultColumns] = useState<CustomColumn[]>([]);
  const [isLoadingColumns, setIsLoadingColumns] = useState(true);
  const [columns, setColumns] = useState<CustomColumn[]>([]);
  const [columnsUploadError, setColumnsUploadError] = useState<string | null>(null);

  // Fetch regulations on mount
  useEffect(() => {
    const fetchRegulations = async () => {
      try {
        const response = await fetch(getUrl('/api/compliance/regulations'));
        if (response.ok) {
          const data = await response.json() as { regulations: Regulation[] };
          const regulationsList = data.regulations || [];
          setRegulations(regulationsList);
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

  // Fetch default prompts on mount
  useEffect(() => {
    const fetchDefaultPrompts = async () => {
      try {
        const response = await fetch(getUrl('/api/compliance/default-prompts'));
        if (response.ok) {
          const data = await response.json() as { systemPrompt: string };
          const defaultSys = data.systemPrompt || '';
          setDefaultSystemPrompt(defaultSys);
          
          // Try to load saved prompts from localStorage
          const savedPrompts = loadCustomPrompts();
          if (savedPrompts) {
            setSystemPrompt(savedPrompts.systemPrompt);
          } else {
            // Use default prompts
            setSystemPrompt(defaultSys);
          }
        }
      } catch (error) {
        console.error('Error fetching default prompts:', error);
      } finally {
        setIsLoadingPrompts(false);
      }
    };
    fetchDefaultPrompts();
  }, []);

  // Fetch default columns on mount
  useEffect(() => {
    const fetchDefaultColumns = async () => {
      try {
        const response = await fetch(getUrl('/api/compliance/default-columns'));
        if (response.ok) {
          const data = await response.json() as { columns: CustomColumn[] };
          const columnsList = data.columns || [];
          setDefaultColumns(columnsList);
          
          // Try to load saved columns from localStorage
          const savedColumns = loadCustomColumns();
          if (savedColumns && savedColumns.length > 0) {
            setColumns(savedColumns);
          } else {
            // Use default columns
            setColumns(columnsList);
          }
        }
      } catch (error) {
        console.error('Error fetching default columns:', error);
      } finally {
        setIsLoadingColumns(false);
      }
    };
    fetchDefaultColumns();
  }, []);

  // File helpers
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
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/plain',
      'text/markdown',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'text/csv',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'application/vnd.ms-excel.sheet.macroEnabled.12'
    ]);
    if (file.type && supportedMimeTypes.has(file.type)) return true;
    const name = file.name.toLowerCase();
    return name.endsWith('.pdf') || name.endsWith('.docx') || name.endsWith('.doc') || name.endsWith('.txt') || name.endsWith('.md') || name.endsWith('.pptx') || name.endsWith('.csv') || name.endsWith('.xlsx') || name.endsWith('.xls') || name.endsWith('.xlsm');
  }, []);

  const addFiles = useCallback((filesToAdd: File[]) => {
    setSelectedFiles(prev => {
      const existingNames = new Set(prev.map(file => file.name.toLowerCase()));
      const uniqueFiles = filesToAdd.filter(file => {
        const name = file.name.toLowerCase();
        if (existingNames.has(name)) return false;
        existingNames.add(name);
        return true;
      });
      return uniqueFiles.length > 0 ? [...prev, ...uniqueFiles] : prev;
    });
  }, []);

  // File drag handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(isSupportedFile);
    if (files.length > 0) addFiles(files);
  }, [addFiles, isSupportedFile]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files).filter(isSupportedFile) : [];
    if (files.length > 0) addFiles(files);
    e.target.value = '';
  }, [addFiles, isSupportedFile]);

  const handleRemoveFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  // Policy handlers
  const handleSelectAll = useCallback((checked: boolean) => {
    setSelectAll(checked);
    if (checked) {
      const allFilenames = new Set(regulations.map(r => r.filename));
      userUploadedPolicies.forEach(policy => allFilenames.add(policy.id));
      setSelectedRegulations(allFilenames);
    } else {
      setSelectedRegulations(new Set());
    }
  }, [regulations, userUploadedPolicies]);

  const handleRegulationToggle = useCallback((filename: string, checked: boolean) => {
    setSelectedRegulations(prev => {
      const newSet = new Set(prev);
      if (checked) newSet.add(filename);
      else newSet.delete(filename);
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

  // Policy modal handlers
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
          if (existingNames.has(name)) return false;
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
          if (existingNames.has(name)) return false;
          existingNames.add(name);
          return true;
        });
        return [...prev, ...uniqueFiles];
      });
    }
    e.target.value = '';
  }, [isSupportedFile]);

  const handleAddPolicyFiles = useCallback(() => {
    if (policyFilesToAdd.length > 0) {
      const newPolicies: UserUploadedPolicy[] = policyFilesToAdd.map(file => ({
        file,
        id: `user_policy_${Date.now()}_${Math.random().toString(36).substr(2, 9)}_${file.name}`
      }));
      
      setUserUploadedPolicies(prev => {
        const existingNames = new Set(prev.map(p => p.file.name.toLowerCase()));
        const uniquePolicies = newPolicies.filter(p => !existingNames.has(p.file.name.toLowerCase()));
        
        setSelectedRegulations(prevRegs => {
          const newSet = new Set(prevRegs);
          uniquePolicies.forEach(policy => newSet.add(policy.id));
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
      if (checked) newSet.add(policyId);
      else newSet.delete(policyId);
      const totalPolicies = regulations.length + userUploadedPolicies.length;
      setSelectAll(newSet.size === totalPolicies);
      return newSet;
    });
  }, [regulations.length, userUploadedPolicies.length]);

  const getPolicyDisplayName = useCallback((filename: string) => {
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
      setDuplicateNameError(null);
    }
  }, [userUploadedPolicies, getPolicyName]);

  const handleSaveEdit = useCallback((policyId: string) => {
    const trimmedValue = editingValue.trim();
    if (trimmedValue === '') {
      setDuplicateNameError('Policy name cannot be empty');
      return;
    }
    
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

  // Handle ESC key to close modals
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isPolicyModalOpen) {
          // Close policy modal first if open
          setIsPolicyModalOpen(false);
          setPolicyFilesToAdd([]);
        } else {
          // Close main wizard modal
          onCancel();
        }
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isPolicyModalOpen, onCancel]);

  // Prompts handlers
  const handleSystemPromptChange = useCallback((value: string) => {
    setSystemPrompt(value);
    saveCustomPrompts({ systemPrompt: value });
  }, []);

  const handleResetPromptsToDefaults = useCallback(() => {
    setSystemPrompt(defaultSystemPrompt);
    saveCustomPrompts({ systemPrompt: defaultSystemPrompt });
    setPromptsUploadError(null);
  }, [defaultSystemPrompt]);

  // Helper function to generate timestamp for filenames
  const getTimestamp = useCallback(() => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day}-${hours}${minutes}${seconds}`;
  }, []);

  // Download prompts configuration
  const handleDownloadPromptsConfig = useCallback(() => {
    const config = {
      systemPrompt
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `prompts-config-${getTimestamp()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [systemPrompt, getTimestamp]);

  // Upload prompts configuration
  const handleUploadPromptsConfig = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setPromptsUploadError(null);
    
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        const config = JSON.parse(content);
        
        // Validate structure
        if (typeof config !== 'object' || config === null) {
          setPromptsUploadError('Invalid configuration file: must be a JSON object');
          return;
        }
        
        if (typeof config.systemPrompt !== 'string') {
          setPromptsUploadError('Invalid configuration: systemPrompt must be a string');
          return;
        }
        
        if (config.systemPrompt.trim().length === 0) {
          setPromptsUploadError('Invalid configuration: systemPrompt cannot be empty');
          return;
        }
        
        // Apply configuration
        setSystemPrompt(config.systemPrompt);
        saveCustomPrompts({ systemPrompt: config.systemPrompt });
        setPromptsUploadError(null);
      } catch {
        setPromptsUploadError('Invalid JSON file: could not parse configuration');
      }
    };
    reader.onerror = () => {
      setPromptsUploadError('Error reading file');
    };
    reader.readAsText(file);
    
    // Reset input so the same file can be selected again
    e.target.value = '';
  }, []);

  // Columns handlers
  const handleColumnsChange = useCallback((newColumns: CustomColumn[]) => {
    setColumns(newColumns);
    saveCustomColumns(newColumns);
  }, []);

  const handleResetColumnsToDefaults = useCallback(() => {
    setColumns(defaultColumns);
    saveCustomColumns(defaultColumns);
    setColumnsUploadError(null);
  }, [defaultColumns]);

  // Download columns configuration
  const handleDownloadColumnsConfig = useCallback(() => {
    const config = {
      columns
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `columns-config-${getTimestamp()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [columns, getTimestamp]);

  // Upload columns configuration
  const handleUploadColumnsConfig = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setColumnsUploadError(null);
    
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        const config = JSON.parse(content);
        
        // Validate structure
        if (typeof config !== 'object' || config === null) {
          setColumnsUploadError('Invalid configuration file: must be a JSON object');
          return;
        }
        
        if (!Array.isArray(config.columns)) {
          setColumnsUploadError('Invalid configuration: columns must be an array');
          return;
        }
        
        if (config.columns.length === 0) {
          setColumnsUploadError('Invalid configuration: columns array cannot be empty');
          return;
        }
        
        // Validate each column
        for (let i = 0; i < config.columns.length; i++) {
          const col = config.columns[i];
          
          if (typeof col !== 'object' || col === null) {
            setColumnsUploadError(`Invalid configuration: column at index ${i} must be an object`);
            return;
          }
          
          if (typeof col.name !== 'string' || col.name.trim().length === 0) {
            setColumnsUploadError(`Invalid configuration: column at index ${i} must have a non-empty name`);
            return;
          }
          
          if (typeof col.description !== 'string' || col.description.trim().length === 0) {
            setColumnsUploadError(`Invalid configuration: column at index ${i} must have a non-empty description`);
            return;
          }
          
          // Validate optional fields if present
          if (col.isDefault !== undefined && typeof col.isDefault !== 'boolean') {
            setColumnsUploadError(`Invalid configuration: column at index ${i} has invalid isDefault (must be boolean)`);
            return;
          }
          
          if (col.type !== undefined && typeof col.type !== 'string') {
            setColumnsUploadError(`Invalid configuration: column at index ${i} has invalid type (must be string)`);
            return;
          }
          
          if (col.enum !== undefined) {
            if (!Array.isArray(col.enum)) {
              setColumnsUploadError(`Invalid configuration: column at index ${i} has invalid enum (must be array)`);
              return;
            }
            for (const enumVal of col.enum) {
              if (typeof enumVal !== 'string') {
                setColumnsUploadError(`Invalid configuration: column at index ${i} has invalid enum value (must be string)`);
                return;
              }
            }
          }
        }
        
        // Build validated columns array
        const validatedColumns: CustomColumn[] = config.columns.map((col: Record<string, unknown>) => ({
          name: col.name as string,
          description: col.description as string,
          isDefault: col.isDefault as boolean | undefined,
          type: col.type as string | undefined,
          enum: col.enum as string[] | undefined
        }));
        
        // Apply configuration
        setColumns(validatedColumns);
        saveCustomColumns(validatedColumns);
        setColumnsUploadError(null);
      } catch {
        setColumnsUploadError('Invalid JSON file: could not parse configuration');
      }
    };
    reader.onerror = () => {
      setColumnsUploadError('Error reading file');
    };
    reader.readAsText(file);
    
    // Reset input so the same file can be selected again
    e.target.value = '';
  }, []);

  // Validation for each step
  const canProceed = useMemo(() => {
    switch (currentStep) {
      case 'files':
        return selectedFiles.length > 0;
      case 'policies':
        return selectedRegulations.size > 0;
      case 'define-prompts':
        // System prompt must have some content (not just whitespace) and be within limit
        return systemPrompt.trim().length > 0 && systemPrompt.length <= 6000;
      case 'define-columns':
        // Check if all columns are valid
        if (columns.length === 0) return false;
        for (let i = 0; i < columns.length; i++) {
          const col = columns[i];
          if (validateName(col.name)) return false;
          if (validateDescription(col.description)) return false;
          if (checkDuplicates(columns, i, col.name)) return false;
        }
        return true;
      default:
        return false;
    }
  }, [currentStep, selectedFiles, selectedRegulations, systemPrompt, columns]);

  // Navigation
  const handleNext = useCallback(() => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex]);
    } else {
      // Complete the wizard
      const selectedRegulationsArray = Array.from(selectedRegulations);
      const knowledgeBaseRegulations = selectedRegulationsArray.filter(reg => 
        regulations.some(r => r.filename === reg)
      );
      const selectedUserPolicies = userUploadedPolicies
        .filter(policy => selectedRegulations.has(policy.id));
      const policyCustomNames: Record<string, string> = {};
      selectedUserPolicies.forEach(policy => {
        policyCustomNames[policy.file.name] = policy.customName || policy.file.name;
      });
      
      // Include custom prompts if they differ from defaults
      const customPrompts: CustomPrompts | undefined = 
        (systemPrompt !== defaultSystemPrompt)
          ? { systemPrompt }
          : undefined;
      
      onComplete({
        files: selectedFiles,
        selectedRegulations: knowledgeBaseRegulations,
        userUploadedPolicies: selectedUserPolicies,
        policyCustomNames,
        columns,
        customPrompts
      });
    }
  }, [currentStepIndex, selectedRegulations, regulations, userUploadedPolicies, selectedFiles, columns, systemPrompt, defaultSystemPrompt, onComplete]);

  const handleBack = useCallback(() => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex]);
    }
  }, [currentStepIndex]);

  const isLastStep = currentStepIndex === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm"
        onClick={onCancel}
      />
      
      {/* Modal */}
      <div 
        className="relative bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Compliance Checker</h2>
          <button
            onClick={onCancel}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <MdClose className="w-5 h-5" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <div className="flex items-center justify-center gap-4 max-w-3xl mx-auto">
            {STEPS.map((step, index) => {
              const isActive = index === currentStepIndex;
              const isCompleted = index < currentStepIndex;
              
              return (
                <div key={step} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div 
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                        isActive 
                          ? 'bg-primary text-white' 
                          : isCompleted 
                            ? 'bg-green-500 text-white' 
                            : 'bg-gray-200 text-gray-500'
                      }`}
                    >
                      {isCompleted ? <MdCheck className="w-5 h-5" /> : index + 1}
                    </div>
                    <span className={`mt-1 text-xs font-medium whitespace-nowrap ${
                      isActive ? 'text-primary' : isCompleted ? 'text-green-600' : 'text-gray-400'
                    }`}>
                      {STEP_LABELS[step]}
                    </span>
                  </div>
                  {index < STEPS.length - 1 && (
                    <div className={`w-16 h-0.5 mx-4 ${
                      isCompleted ? 'bg-green-500' : 'bg-gray-200'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-scroll p-6 min-h-[480px] wizard-scrollbar">
          {/* Step 1: Files */}
          {currentStep === 'files' && (
            <div className="flex flex-col gap-4 h-full">
              <div className="text-center mb-2">
                <h3 className="text-lg font-semibold text-gray-900">Upload Documents</h3>
                <p className="text-sm text-gray-500">Select the files you want to check for compliance</p>
              </div>
              
              <div
                className={`
                  flex flex-col items-center justify-center
                  w-full flex-1 min-h-[320px]
                  border-2 border-dashed rounded-lg
                  transition-colors cursor-pointer
                  ${isDragging 
                    ? 'border-primary bg-primary/5' 
                    : 'border-gray-300 bg-gray-50 hover:border-gray-400'
                  }
                `}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById('wizard-file-input')?.click()}
              >
                {selectedFiles.length === 0 ? (
                  <>
                    <MdCloudUpload className="w-12 h-12 text-gray-400 mb-4" />
                    <p className="text-gray-600 text-sm mb-2">
                      Drop files here or click to browse
                    </p>
                    <p className="text-gray-400 text-xs">
                      Supported: .pdf, .docx, .doc, .pptx, .txt, .md, .csv, .xlsx, .xls
                    </p>
                  </>
                ) : (
                  <div className="w-full p-4" onClick={(e) => e.stopPropagation()}>
                    <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
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
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRemoveFile(index);
                            }}
                            className="text-gray-400 hover:text-red-500 transition-colors"
                          >
                            <MdClose className="w-5 h-5" />
                          </button>
                        </div>
                      ))}
                    </div>
                    <label
                      htmlFor="wizard-file-input"
                      className="mt-4 flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-lg cursor-pointer transition-colors"
                    >
                      <MdAdd className="w-4 h-4" />
                      Add More Files
                    </label>
                  </div>
                )}
                <input
                  type="file"
                  accept=".pdf,.docx,.doc,.pptx,.txt,.md,.csv,.xlsx,.xls,.xlsm"
                  multiple
                  onChange={handleFileInput}
                  className="hidden"
                  id="wizard-file-input"
                />
              </div>
            </div>
          )}

          {/* Step 2: Policies */}
          {currentStep === 'policies' && (
            <div className="flex flex-col gap-4">
              <div className="text-center mb-2">
                <h3 className="text-lg font-semibold text-gray-900">Select Policies</h3>
                <p className="text-sm text-gray-500">Choose which policies to check your documents against</p>
              </div>
              
              {isLoadingRegulations ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-2 pb-2 border-b border-gray-200">
                    <input
                      type="checkbox"
                      id="wizard-select-all"
                      checked={selectAll}
                      onChange={(e) => handleSelectAll(e.target.checked)}
                      className="w-4 h-4 accent-primary border-gray-300 rounded focus:ring-primary cursor-pointer"
                    />
                    <label htmlFor="wizard-select-all" className="text-sm font-medium text-gray-700 cursor-pointer">
                      Select All
                    </label>
                    <span className="ml-auto text-sm text-gray-500">
                      ({selectedRegulations.size}/{regulations.length + userUploadedPolicies.length})
                    </span>
                  </div>
                  
                  <div className="flex flex-col gap-2 max-h-64 overflow-y-auto">
                    {regulations.map((regulation) => (
                      <div key={regulation.filename} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id={`wizard-regulation-${regulation.filename}`}
                          checked={selectedRegulations.has(regulation.filename)}
                          onChange={(e) => handleRegulationToggle(regulation.filename, e.target.checked)}
                          className="w-4 h-4 accent-primary border-gray-300 rounded focus:ring-primary cursor-pointer"
                        />
                        <label
                          htmlFor={`wizard-regulation-${regulation.filename}`}
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
                          id={`wizard-policy-${policy.id}`}
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
                                  setDuplicateNameError(null);
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
                                className="text-gray-400 hover:text-green-600 transition-colors"
                              >
                                <MdCheck className="w-4 h-4" />
                              </button>
                              <button
                                onClick={handleCancelEdit}
                                className="text-gray-400 hover:text-red-500 transition-colors"
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
                              htmlFor={`wizard-policy-${policy.id}`}
                              className="text-sm text-gray-700 cursor-pointer flex-1"
                            >
                              {getPolicyName(policy)}
                            </label>
                            <button
                              onClick={() => handleStartEdit(policy.id)}
                              className="text-gray-400 hover:text-blue-500 transition-colors"
                            >
                              <MdEdit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleRemovePolicyFile(policy.id)}
                              className="text-gray-400 hover:text-red-500 transition-colors"
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
                    className="mt-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-lg transition-colors flex items-center gap-2 justify-center"
                  >
                    <MdAdd className="w-4 h-4" />
                    Add more policies
                  </button>
                </div>
              )}

              {selectedRegulations.size === 0 && (
                <p className="text-red-500 text-sm text-center">Please select at least one policy to proceed</p>
              )}
            </div>
          )}

          {/* Step 3: Define Prompts */}
          {currentStep === 'define-prompts' && (
            <div className="flex flex-col gap-4">
              <div className="text-center mb-2">
                <h3 className="text-lg font-semibold text-gray-900">Define Prompts</h3>
                <p className="text-sm text-gray-500">
                  Customize the prompts sent to the AI for compliance evaluation.
                </p>
              </div>
              
              {isLoadingPrompts ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-end gap-3 mb-1">
                    <button
                      onClick={handleDownloadPromptsConfig}
                      className="flex items-center gap-1 text-sm text-gray-500 hover:text-primary transition-colors"
                    >
                      <MdDownload className="w-4 h-4" />
                      Download
                    </button>
                    <label
                      htmlFor="wizard-prompts-config-upload"
                      className="flex items-center gap-1 text-sm text-gray-500 hover:text-primary transition-colors cursor-pointer"
                    >
                      <MdUpload className="w-4 h-4" />
                      Upload
                    </label>
                    <input
                      type="file"
                      accept=".json"
                      onChange={handleUploadPromptsConfig}
                      className="hidden"
                      id="wizard-prompts-config-upload"
                    />
                    <span className="text-gray-300">|</span>
                    <button
                      onClick={handleResetPromptsToDefaults}
                      className="text-sm text-gray-500 hover:text-primary transition-colors"
                    >
                      Restore Defaults
                    </button>
                  </div>
                  {promptsUploadError && (
                    <p className="text-red-500 text-sm text-right">{promptsUploadError}</p>
                  )}
                  
                  {/* System Prompt */}
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-gray-700">System Prompt</label>
                    <p className="text-xs text-gray-500">
                      Defines the AI's role and behavior. The fixed prefix below cannot be changed.
                    </p>
                    
                    {/* Fixed prefix (read-only) */}
                    <div className="bg-gray-100 border border-gray-200 rounded-t-lg px-3 py-2 text-sm text-gray-600 font-mono">
                      {FIXED_SYSTEM_PREFIX}
                    </div>
                    
                    {/* Editable system prompt */}
                    <textarea
                      value={systemPrompt}
                      onChange={(e) => handleSystemPromptChange(e.target.value)}
                      placeholder="Enter your system prompt instructions..."
                      className="w-full h-[500px] min-h-[200px] px-3 py-2 border border-gray-300 rounded-b-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-y font-mono -mt-px"
                    />
                    <span className={`text-xs ${systemPrompt.length > 6000 ? 'text-red-500' : 'text-gray-500'}`}>
                      {systemPrompt.length}/6000 characters
                    </span>
                    <p className="text-xs text-gray-400">
                      Column definitions are automatically appended based on your output columns configuration.
                    </p>
                  </div>
                  
                  {/* Validation messages */}
                  {systemPrompt.trim().length === 0 && (
                    <p className="text-red-500 text-sm text-center mt-2">System prompt must have content to proceed</p>
                  )}
                  {systemPrompt.length > 6000 && (
                    <p className="text-red-500 text-sm text-center mt-2">System prompt exceeds 6000 character limit</p>
                  )}
                </>
              )}
            </div>
          )}

          {/* Step 4: Define Output Columns */}
          {currentStep === 'define-columns' && (
            <div className="flex flex-col gap-4">
              <div className="text-center mb-2">
                <h3 className="text-lg font-semibold text-gray-900">Define Output Columns</h3>
                <p className="text-sm text-gray-500">Customize the columns in your compliance report. Add, remove, or modify columns as needed.</p>
              </div>
              
              {isLoadingColumns ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-1">
                    <button
                      onClick={() => {
                        const newColumn: CustomColumn = {
                          name: '',
                          description: '',
                          isDefault: false
                        };
                        handleColumnsChange([...columns, newColumn]);
                      }}
                      className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-lg transition-colors"
                    >
                      <MdAdd className="w-5 h-5" />
                      Add Column
                    </button>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={handleDownloadColumnsConfig}
                        className="flex items-center gap-1 text-sm text-gray-500 hover:text-primary transition-colors"
                      >
                        <MdDownload className="w-4 h-4" />
                        Download
                      </button>
                      <label
                        htmlFor="wizard-columns-config-upload"
                        className="flex items-center gap-1 text-sm text-gray-500 hover:text-primary transition-colors cursor-pointer"
                      >
                        <MdUpload className="w-4 h-4" />
                        Upload
                      </label>
                      <input
                        type="file"
                        accept=".json"
                        onChange={handleUploadColumnsConfig}
                        className="hidden"
                        id="wizard-columns-config-upload"
                      />
                      <span className="text-gray-300">|</span>
                      <button
                        onClick={handleResetColumnsToDefaults}
                        className="text-sm text-gray-500 hover:text-primary transition-colors"
                      >
                        Restore Defaults
                      </button>
                    </div>
                  </div>
                  {columnsUploadError && (
                    <p className="text-red-500 text-sm text-right">{columnsUploadError}</p>
                  )}
                  <ColumnManager 
                    columns={columns} 
                    onChange={handleColumnsChange}
                  />
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={currentStepIndex === 0 ? onCancel : handleBack}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <MdChevronLeft className="w-5 h-5" />
            {currentStepIndex === 0 ? 'Cancel' : 'Back'}
          </button>
          
          <button
            onClick={handleNext}
            disabled={!canProceed}
            className={`flex items-center gap-2 px-6 py-2 rounded-lg transition-colors ${
              canProceed 
                ? 'bg-primary text-white hover:bg-primary/90' 
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {isLastStep ? (
              <>
                <MdUpload className="w-5 h-5" />
                Start Verification
              </>
            ) : (
              <>
                Next
                <MdChevronRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Policy Upload Modal (nested) */}
      {isPolicyModalOpen && (
        <div 
          className="fixed inset-0 z-60 flex items-center justify-center"
          onClick={() => {
            setIsPolicyModalOpen(false);
            setPolicyFilesToAdd([]);
          }}
        >
          <div className="absolute inset-0 bg-gray-900/30" />
          <div 
            className="relative bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
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
                w-full min-h-[200px]
                border-2 border-dashed rounded-lg
                transition-colors
                ${isPolicyDragging 
                  ? 'border-primary bg-primary/5' 
                  : 'border-gray-300 bg-gray-50'
                }
                ${policyFilesToAdd.length > 0 ? 'p-4' : 'p-8'}
              `}
              onDragOver={handlePolicyDragOver}
              onDragLeave={handlePolicyDragLeave}
              onDrop={handlePolicyDrop}
            >
              {policyFilesToAdd.length === 0 ? (
                <>
                  <MdCloudUpload className="w-10 h-10 text-gray-400 mb-3" />
                  <p className="text-gray-600 text-sm mb-2">
                    Drop files here or click to browse
                  </p>
                  <p className="text-gray-400 text-xs mb-3">
                    Supported: .pdf, .docx, .doc, .pptx, .txt, .md, .csv, .xlsx, .xls
                  </p>
                  <label
                    htmlFor="wizard-policy-file-input"
                    className="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary/90 cursor-pointer transition-colors flex items-center gap-2"
                  >
                    <MdFolderOpen className="w-4 h-4" />
                    Select Files
                  </label>
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.md,.pptx,.csv,.xlsx,.xls,.xlsm"
                    multiple
                    onChange={handlePolicyFileInput}
                    className="hidden"
                    id="wizard-policy-file-input"
                  />
                </>
              ) : (
                <div className="w-full flex flex-col gap-3">
                  <div className="flex flex-col gap-2 max-h-40 overflow-y-auto">
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
                          className="text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <MdClose className="w-5 h-5" />
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-3">
                    <label
                      htmlFor="wizard-policy-file-input"
                      className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-lg cursor-pointer transition-colors flex items-center gap-2 justify-center"
                    >
                      <MdAdd className="w-4 h-4" />
                      Add More
                    </label>
                    <button
                      onClick={handleAddPolicyFiles}
                      className="flex-1 px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2 justify-center"
                    >
                      <MdUpload className="w-4 h-4" />
                      Add Policies
                    </button>
                  </div>
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.md,.pptx,.csv,.xlsx,.xls,.xlsm"
                    multiple
                    onChange={handlePolicyFileInput}
                    className="hidden"
                    id="wizard-policy-file-input"
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

