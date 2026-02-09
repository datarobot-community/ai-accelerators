import { MdErrorOutline, MdRefresh } from 'react-icons/md';
import { type InvalidFile } from '../../types/compliance';

interface InvalidDocumentViewProps {
  invalidFiles: InvalidFile[];
  onTryDifferentFile?: () => void;
}

export function InvalidDocumentView({ invalidFiles, onTryDifferentFile }: InvalidDocumentViewProps) {
  return (
    <div className="w-full h-full">
      <div className="border border-red-200 rounded-lg bg-red-50 p-8 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <MdErrorOutline className="w-6 h-6 text-red-600" />
            </div>
            <h2 className="text-2xl font-bold text-red-900">
              {invalidFiles.length === 1 ? 'Invalid File' : 'Invalid Files'}
            </h2>
          </div>
          
          <p className="text-base text-red-800 mb-4">
            {invalidFiles.length === 1 
              ? 'The uploaded document could not be verified because it does not meet the requirements for compliance verification.'
              : 'Some uploaded documents could not be verified because they do not meet the requirements for compliance verification.'}
          </p>
          
          <div className="bg-white rounded-md border border-red-200 p-4 mb-6 max-h-96 overflow-y-auto">
            <div className="flex flex-col gap-4">
              {invalidFiles.map((invalidFile, index) => (
                <div key={index} className="flex items-start gap-2">
                  <div className="flex-shrink-0 mt-0.5">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      Invalid
                    </span>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-gray-900 mb-1">
                      File: <span className="font-mono text-xs">{invalidFile.filename}</span>
                    </h3>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {invalidFile.reason}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-red-100 rounded-md p-4 mb-6">
            <h3 className="text-sm font-semibold text-red-900 mb-2">What does this mean?</h3>
            <p className="text-sm text-red-800">
              {invalidFiles.length === 1 
                ? 'The document you uploaded is not relevant to telecommunications or domain policy compliance.'
                : 'The documents you uploaded are not relevant to telecommunications or domain policy compliance.'}
              {' '}Please upload document(s) that describe telecom services, plans, policies, or regulations 
              that need to be verified for compliance.
            </p>
          </div>

          {onTryDifferentFile && (
            <div className="flex items-center gap-3">
              <button
                onClick={onTryDifferentFile}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                <MdRefresh className="w-4 h-4" />
                Try a Different File
              </button>
            </div>
          )}
        </div>
    </div>
  );
}

