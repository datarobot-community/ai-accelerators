export interface ComplianceIssue {
  regulation_file_name: string;
  regulation_file_url: string;
  regulation_clause_section: string;
  regulation_clause_text: string;
  cvp_evidence: string;
  recommended_criticality: 'Critical' | 'Medium' | 'Low';
  explanation: string;
  recommendation: string;
  input_file_name?: string; // Name of the input file (only present when multiple files are uploaded)
  // Allow dynamic keys for custom columns
  [key: string]: string | undefined;
}

export interface InvalidFile {
  filename: string;
  reason: string;
}

export interface CustomColumn {
  name: string;
  description: string;
  isDefault?: boolean;
  type?: string;
  enum?: string[];
}

export interface Regulation {
  filename: string;
  displayName: string;
}

export interface UserUploadedPolicy {
  file: File;
  id: string;
  customName?: string;
}

export interface CustomPrompts {
  systemPrompt: string;
}

export interface WizardData {
  files: File[];
  selectedRegulations: string[];
  userUploadedPolicies: UserUploadedPolicy[];
  policyCustomNames: Record<string, string>;
  columns: CustomColumn[];
  customPrompts?: CustomPrompts;
}

export type ProcessingEvent =
  | { type: 'uploading'; data: { filename: string } }
  | { type: 'parsing'; data: { filename: string } }
  | { type: 'validating'; data: { filename: string } }
  | { type: 'verifying'; data: { regulation_name: string; regulation_index: number; total_regulations: number } }
  | { type: 'regulation_complete'; data: { regulation_name: string; regulation_index: number; total_regulations: number } }
  | { type: 'issues_delta'; data: { issues: ComplianceIssue[] } }
  | { type: 'complete'; data: { issues: ComplianceIssue[] } }
  | { type: 'document_invalid'; data: { filename: string; reason: string } }
  | { type: 'file_validated'; data: { filename: string } }
  | { type: 'error'; data: { message: string } };

export interface ProcessingStep {
  id: string;
  message: string;
  timestamp: number;
  regulationIndex?: number; // Track which regulation this step belongs to
  isComplete?: boolean; // Track if this regulation step is complete
}
