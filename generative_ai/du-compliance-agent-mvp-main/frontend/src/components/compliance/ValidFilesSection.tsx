import { MdCheckCircle, MdVerified } from 'react-icons/md';
import { AiOutlineLoading3Quarters } from 'react-icons/ai';

interface ValidFilesSectionProps {
  validFiles: string[];
  isProcessing: boolean;
  hasIssues: boolean;
  onVerifyFiles: () => void;
}

export function ValidFilesSection({ validFiles, isProcessing, hasIssues, onVerifyFiles }: ValidFilesSectionProps) {
  const isSingular = validFiles.length === 1;
  const fileText = isSingular ? 'file has' : 'files have';
  const processingText = isProcessing 
    ? (isSingular ? 'is being processed' : 'are being processed')
    : (isSingular ? 'has been processed' : 'have been processed');
  
  return (
    <div className="w-full">
      <div className="border border-green-200 rounded-lg bg-green-50 p-8 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
            <MdCheckCircle className="w-6 h-6 text-green-600" />
          </div>
          <h3 className="text-2xl font-bold text-green-900">
            {isSingular ? "Valid File" : "Valid Files"}
          </h3>
        </div>
        
        <p className="text-base text-green-800 mb-4">
          The following {fileText} been validated and {processingText} in the background.
        </p>
        
        <div className="bg-white rounded-md border border-green-200 p-4 mb-4 max-h-48 overflow-y-auto">
          <ul className="space-y-2">
            {validFiles.map((filename, index) => (
              <li key={index} className="flex items-center gap-2 text-sm text-gray-700">
                <MdVerified className="w-4 h-4 text-green-600 flex-shrink-0" />
                <span className="font-mono text-xs truncate">{filename}</span>
                {isProcessing && (
                  <span className="ml-auto text-xs text-green-600 animate-pulse">Processing...</span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onVerifyFiles}
            disabled={isProcessing && !hasIssues}
            className={`inline-flex items-center gap-2 px-5 py-2.5 text-white text-sm font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
              isProcessing && !hasIssues
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700 focus:ring-green-500'
            }`}
          >
            {isProcessing && !hasIssues ? (
              <>
                <AiOutlineLoading3Quarters className="w-4 h-4 animate-spin" />
                Processing ...
              </>
            ) : (
              <>
                <MdCheckCircle className="w-4 h-4" />
                Show Report
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

