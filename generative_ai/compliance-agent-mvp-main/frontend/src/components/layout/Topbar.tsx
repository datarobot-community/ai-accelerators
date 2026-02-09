import { useState } from 'react';
import { getUrl } from '../../utils/urlUtils';
import { MdChecklist, MdClose } from 'react-icons/md';

// Guidelines for compliance checking
const defaultGuidelines = [
  {
    do: "Use the wizard to upload documents, select policies, and customize prompts/columns",
    dont: "Skip the wizard steps - each step helps configure your compliance check",
  },
  {
    do: "Upload documents in supported formats (PDF, DOCX, DOC, TXT, MD)",
    dont: "Upload unsupported file types, corrupted files, or password-protected documents",
  },
  {
    do: "Select relevant policies from the knowledge base or upload your own custom policies",
    dont: "Select all policies indiscriminately - choose only those relevant to your documents",
  },
  {
    do: "Customize output columns to focus on the compliance aspects that matter to you",
    dont: "Use default columns without considering if they match your reporting needs",
  },
  {
    do: "Wait for document validation - irrelevant documents will be filtered out automatically",
    dont: "Upload documents unrelated to telecom/domain compliance (they'll be rejected)",
  },
  {
    do: "Monitor real-time progress as issues are discovered during verification",
    dont: "Navigate away or close the browser while processing is in progress",
  },
  {
    do: "Review the complete compliance report with all columns, evidence, and recommendations",
    dont: "Ignore the detailed explanations and evidence provided for each issue",
  },
  {
    do: "Download the CSV report to preserve results and share with your team",
    dont: "Rely only on the on-screen view - results are not saved between sessions",
  },
  {
    do: "Click regulation links to view the full policy context for each compliance issue",
    dont: "Make compliance decisions without reviewing the source regulations",
  },
  {
    do: "Save and reuse your custom column/prompt configurations for consistent analysis",
    dont: "Recreate your configurations each time - download and upload them as JSON",
  },
];

export function Topbar() {
  const [isGuidelinesOpen, setIsGuidelinesOpen] = useState(false);

  const handleClick = () => {
    window.location.href = getUrl('/');
  };

  return (
    <>
      <div className="w-full px-8 py-4 flex items-center justify-between gap-6">
        <div className="flex items-center gap-6">
          <img 
            src={getUrl('/dr-icon.svg')}
            alt="DR Logo" 
            className="h-8"
          />
          <button
            onClick={handleClick}
            className="text-gray-500 hover:text-primary transition-colors text-sm cursor-pointer"
          >
            Compliance Checker
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsGuidelinesOpen(true)}
            className="inline-flex items-center justify-center gap-2 px-3 py-1.5 text-sm font-normal text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
          >
            <MdChecklist className="w-4 h-4" />
            <span>Do and Don't</span>
          </button>
        </div>
      </div>

      {/* Dialog/Modal */}
      {isGuidelinesOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/50"
            onClick={() => setIsGuidelinesOpen(false)}
          />
          
          {/* Dialog Content */}
          <div className="relative bg-white rounded-lg shadow-lg max-w-3xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Best Practices for Compliance Checking</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Follow these guidelines to get the most accurate and comprehensive compliance results.
                </p>
              </div>
              <button
                onClick={() => setIsGuidelinesOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors p-1"
                aria-label="Close dialog"
              >
                <MdClose className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="overflow-y-auto p-6">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 bg-green-50 font-semibold text-green-700">
                      Do
                    </th>
                    <th className="text-left p-3 bg-red-50 font-semibold text-red-700">
                      Don't
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {defaultGuidelines.map((guideline, index) => (
                    <tr key={index} className="border-b last:border-b-0">
                      <td className="p-3 align-top bg-green-50/50">
                        <span className="text-sm text-gray-700">{guideline.do}</span>
                      </td>
                      <td className="p-3 align-top bg-red-50/50">
                        <span className="text-sm text-gray-700">{guideline.dont}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
