import { useMemo } from 'react';
import { type ComplianceIssue, type CustomColumn } from '../../types/compliance';
import { MdPrint, MdDownload } from 'react-icons/md';

interface ComplianceTableProps {
  issues: ComplianceIssue[];
  isGenerating?: boolean;
  onTryDifferentFile?: () => void;
  columns?: CustomColumn[];
}

/**
 * Sanitize a column name the same way the backend does.
 * This ensures we can match column names to data keys.
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
 * Default columns configuration matching the backend default schema
 */
const DEFAULT_COLUMNS: CustomColumn[] = [
  { name: 'regulation_file_name', description: 'The name/title of the regulation document', isDefault: true },
  { name: 'regulation_clause_section', description: 'The specific clause or section number/name from the regulation (e.g., \'Section 3.2.1\', \'Clause 5(a)\', \'Article 7.3\'). Include hierarchical references if applicable.', isDefault: true },
  { name: 'regulation_clause_text', description: 'The exact wording of the specific clause or section from the regulation, copied verbatim without any modification, interpretation, or summarization. Include complete text including all subsections and conditions.', isDefault: true },
  { name: 'cvp_evidence', description: 'The EXACT verbatim text from the input sample that demonstrates the non-compliance, missing requirement, or misalignment. Copy the text word-for-word from the input file without any modification, interpretation, summarization, or paraphrasing. Use quotation marks to indicate it\'s a direct quote. If the issue is an absence of required content (nothing in the input addresses the requirement), state \'No relevant content found in the input document\'.', isDefault: true },
  { name: 'recommended_criticality', description: 'The recommended criticality level (Critical, Medium, or Low) based on potential impact, legal consequences, and business risk. Use the criticality assessment guidelines provided.', isDefault: true },
  { name: 'explanation', description: 'A clear, specific explanation of the non-compliance, missing requirement, or misalignment. Articulate the gap between what the regulation requires and what the input provides (or lacks). Explain why this is a compliance issue.', isDefault: true },
  { name: 'recommendation', description: 'Specific, actionable recommendations to address the non-compliance. Provide concrete steps, changes, or additions needed to achieve compliance. Prioritize recommendations and make them implementable.', isDefault: true },
];

/**
 * Get a human-readable display name for a column
 */
function getColumnDisplayName(column: CustomColumn): string {
  const name = column.name;
  // Convert snake_case to Title Case
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get the width class for a column based on its name/type
 */
function getColumnWidthClass(sanitizedName: string): string {
  // Special handling for known column types
  if (sanitizedName === 'regulation_file_name' || sanitizedName === 'regulation_clause_section') {
    return 'w-48';
  }
  if (sanitizedName === 'input_file_name') {
    return 'w-48';
  }
  if (sanitizedName === 'regulation_clause_text') {
    return 'w-96';
  }
  if (sanitizedName === 'cvp_evidence') {
    return 'w-64';
  }
  if (sanitizedName === 'recommended_criticality') {
    return 'w-32';
  }
  if (sanitizedName === 'explanation' || sanitizedName === 'recommendation') {
    return 'w-80';
  }
  // Default width for custom columns
  return 'w-64';
}

/**
 * Render a cell value with special handling for certain column types
 */
function renderCellValue(
  issue: ComplianceIssue, 
  sanitizedName: string, 
  value: string | undefined
): React.ReactNode {
  // Special rendering for criticality column
  if (sanitizedName === 'recommended_criticality') {
    const criticality = value || '';
    return (
      <span
        className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
          criticality === 'Critical'
            ? 'bg-red-100 text-red-800'
            : criticality === 'Medium'
            ? 'bg-yellow-100 text-yellow-800'
            : 'bg-blue-100 text-blue-800'
        }`}
      >
        {criticality}
      </span>
    );
  }
  
  // Special rendering for regulation file name with link
  if (sanitizedName === 'regulation_file_name') {
    return (
      <>
        <a
          href={issue.regulation_file_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:text-primary/80 hover:underline block mb-1 break-words"
          title={value}
        >
          {value}
        </a>
        {issue.regulation_clause_section && (
          <div className="text-gray-700 break-words">
            {issue.regulation_clause_section}
          </div>
        )}
      </>
    );
  }
  
  // Default rendering
  return value || '';
}

export function ComplianceTable({ 
  issues, 
  isGenerating = false, 
  onTryDifferentFile,
  columns 
}: ComplianceTableProps) {
  const handlePrint = () => {
    window.print();
  };

  // Check if multiple files were uploaded by checking if issues have different input_file_name values
  const hasMultipleFiles = useMemo(() => {
    if (!issues || issues.length === 0) return false;
    const fileNames = new Set<string>();
    for (const issue of issues) {
      const fileName = issue.input_file_name;
      if (fileName) {
        fileNames.add(fileName);
        if (fileNames.size > 1) return true;
      }
    }
    return false;
  }, [issues]);

  // Determine which columns to display
  // If custom columns are provided and non-empty, use them
  // Otherwise fall back to default columns
  const displayColumns = useMemo(() => {
    if (columns && columns.length > 0) {
      return columns;
    }
    return DEFAULT_COLUMNS;
  }, [columns]);

  // Always filter out regulation_clause_section column - it's always shown embedded in regulation_file_name
  // Also conditionally include input_file_name column only when multiple files are present
  const visibleColumns = useMemo(() => {
    const filtered = displayColumns.filter(col => {
      const sanitized = sanitizeColumnName(col.name);
      // Filter out regulation_clause_section (always embedded in regulation_file_name)
      return sanitized !== 'regulation_clause_section';
    });
    
    // Add input_file_name column at the beginning if multiple files are present
    if (hasMultipleFiles) {
      const hasInputFileName = filtered.some(col => sanitizeColumnName(col.name) === 'input_file_name');
      if (!hasInputFileName) {
        // Insert input_file_name column at the beginning
        return [
          { name: 'input_file_name', description: 'The name of the input file that was evaluated', isDefault: true },
          ...filtered
        ];
      }
    }
    
    return filtered;
  }, [displayColumns, hasMultipleFiles]);

  // Create mapping from original name to sanitized key
  // Use visibleColumns to include dynamically added columns like input_file_name
  const columnKeyMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const col of visibleColumns) {
      map[col.name] = sanitizeColumnName(col.name);
    }
    return map;
  }, [visibleColumns]);

  const handleDownloadCsv = () => {
    if (!issues || issues.length === 0) return;

    // Build CSV columns: use displayColumns (not visibleColumns) to include regulation_clause_section
    // This ensures the CSV export contains all data, even columns hidden from table display
    const csvColumns = [...displayColumns];
    // Add input_file_name column at the beginning if multiple files are present
    if (hasMultipleFiles) {
      const hasInputFileName = csvColumns.some(col => sanitizeColumnName(col.name) === 'input_file_name');
      if (!hasInputFileName) {
        csvColumns.unshift({ name: 'input_file_name', description: 'The name of the input file that was evaluated', isDefault: true });
      }
    }

    const headers = csvColumns.map(col => getColumnDisplayName(col));
    // Add Regulation File URL at the end for reference
    headers.push('Regulation File URL');

    const escapeCell = (value: unknown) => {
      const stringValue = value === null || value === undefined ? '' : String(value);
      // Replace all line break variations with spaces to prevent CSV formatting issues
      const normalized = stringValue
        .replace(/\r\n/g, ' ')  // Windows line endings first
        .replace(/\n/g, ' ')    // Unix line endings
        .replace(/\r/g, ' ');   // Mac/standalone carriage returns
      // Escape double quotes for CSV format
      const escaped = normalized.replace(/"/g, '""');
      return `"${escaped}"`;
    };

    const rows = issues.map((issue) => {
      const cells = csvColumns.map(col => {
        const key = sanitizeColumnName(col.name);
        const value = issue[key];
        return escapeCell(value);
      });
      // Add regulation file URL at the end
      cells.push(escapeCell(issue.regulation_file_url));
      return cells.join(',');
    });

    // Add UTF-8 BOM (Byte Order Mark) to ensure proper encoding recognition
    const BOM = '\uFEFF';
    const csvContent = BOM + [headers.join(','), ...rows].join('\n');
    
    // Use UTF-8 encoding explicitly in the blob
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'compliance_issues.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col flex-1 p-8 gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">
          Compliance Issues Found ({issues.length})
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadCsv}
            disabled={isGenerating || !issues || issues.length === 0}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-md transition-colors ${
              !isGenerating && issues && issues.length > 0
                ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            <MdDownload className="w-4 h-4" />
            Download CSV
          </button>
          <button
            onClick={handlePrint}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-md hover:bg-gray-200 transition-colors"
          >
            <MdPrint className="w-4 h-4" />
            Print
          </button>
        </div>
      </div>

      {issues.length === 0 && !isGenerating ? (
        <div className="border border-blue-200 rounded-lg bg-blue-50 p-6">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <svg
                className="w-6 h-6 text-blue-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-base font-semibold text-blue-900 mb-1" style={{ fontSize: "1.1rem" }}>
                No compliance issues were detected in the uploaded file. This could mean:
              </h3>
              <ul
                className="mt-2 text-base text-blue-800 list-disc list-inside space-y-1"
                style={{ fontSize: "1.1rem" }}
              >
                <li>The file content may not have been parsed correctly</li>
                <li>The file is fully compliant with all regulations</li> 
              </ul>
              <p
                className="mt-3 text-base text-blue-800"
                style={{ fontSize: "1.1rem" }}
              >
                Please ensure you've uploaded a document related to telecom or domain policy compliance for accurate results.
              </p>
              {onTryDifferentFile && (
                <div className="mt-4">
                  <button
                    onClick={onTryDifferentFile}
                    className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                  >
                    Try a Different File
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full table-fixed">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {visibleColumns.map((col) => {
                  const sanitizedName = columnKeyMap[col.name];
                  return (
                    <th 
                      key={col.name}
                      className={`text-left text-xs font-medium text-gray-600 px-4 py-3 ${getColumnWidthClass(sanitizedName)}`}
                    >
                      {getColumnDisplayName(col)}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {issues.map((issue, index) => (
                <tr key={index} className="hover:bg-gray-50 transition-colors">
                  {visibleColumns.map((col) => {
                    const sanitizedName = columnKeyMap[col.name];
                    const value = issue[sanitizedName] as string | undefined;
                    return (
                      <td 
                        key={col.name}
                        className={`px-4 py-3 text-sm text-gray-700 ${getColumnWidthClass(sanitizedName)} whitespace-normal`}
                      >
                        {renderCellValue(issue, sanitizedName, value)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      )}
    </div>
  );
}
