import { useState, useCallback, useRef } from 'react';
import { PageLayout } from './components/layout/PageLayout';
import { ComplianceWizardModal } from './components/compliance/ComplianceWizardModal';
import { ProcessingView } from './components/compliance/ProcessingView';
import { ProcessingStep } from './components/compliance/ProcessingStep';
import { ComplianceTable } from './components/compliance/ComplianceTable';
import { InvalidDocumentView } from './components/compliance/InvalidDocumentView';
import { ValidFilesSection } from './components/compliance/ValidFilesSection';
import StreamHandler from './utils/StreamHandler';
import { getUrl } from './utils/urlUtils';
import { type ComplianceIssue, type ProcessingEvent, type ProcessingStep as ProcessingStepType, type InvalidFile, type WizardData, type UserUploadedPolicy, type CustomColumn } from './types/compliance';
import { MdChevronLeft, MdChevronRight } from 'react-icons/md';
import './App.css';

type AppState = 'home' | 'wizard' | 'processing' | 'results' | 'invalid';

function App() {
  // TEST MODE: Uncomment the line below to test the "no issues found" message
  // This will show the results view with 0 issues immediately on page load
  // const [state, setState] = useState<AppState>('results');
  
  // PRODUCTION MODE: Use this line normally
  const [state, setState] = useState<AppState>('home');
  
  const [processingSteps, setProcessingSteps] = useState<ProcessingStepType[]>([]);
  const [complianceIssues, setComplianceIssues] = useState<ComplianceIssue[]>([]);
  const [showProcessingSidebar, setShowProcessingSidebar] = useState(false);
  const [isSidebarMinimized, setIsSidebarMinimized] = useState(false);
  const [invalidFiles, setInvalidFiles] = useState<InvalidFile[]>([]);
  const [validFiles, setValidFiles] = useState<string[]>([]);
  const [hasValidFilesProcessing, setHasValidFilesProcessing] = useState(false);
  const [validFilesProcessingComplete, setValidFilesProcessingComplete] = useState(false);
  const [hasStartedVerification, setHasStartedVerification] = useState(false);
  const [customColumns, setCustomColumns] = useState<CustomColumn[]>([]);
  const streamHandlerRef = useRef<StreamHandler<ProcessingEvent> | null>(null);

  const addProcessingStep = useCallback((message: string) => {
    const step: ProcessingStepType = {
      id: `${Date.now()}-${Math.random()}`,
      message,
      timestamp: Date.now()
    };
    setProcessingSteps(prev => [...prev, step]);
  }, []);

  const handleResetToHome = useCallback(() => {
    setState('home');
    setProcessingSteps([]);
    setComplianceIssues([]);
    setShowProcessingSidebar(false);
    setIsSidebarMinimized(false);
    setInvalidFiles([]);
    setValidFiles([]);
    setHasValidFilesProcessing(false);
    setValidFilesProcessingComplete(false);
    setHasStartedVerification(false);
    setCustomColumns([]);
  }, []);

  const handleWizardComplete = useCallback(async (data: WizardData) => {
    const { files, selectedRegulations, userUploadedPolicies, policyCustomNames, columns, customPrompts } = data;
    
    setState('processing');
    setProcessingSteps([]);
    setComplianceIssues([]);
    setShowProcessingSidebar(false);
    setIsSidebarMinimized(false);
    setInvalidFiles([]);
    setValidFiles([]);
    setHasValidFilesProcessing(false);
    setValidFilesProcessingComplete(false);
    setHasStartedVerification(false);
    // Store custom columns for use in report display and CSV export
    setCustomColumns(columns || []);

    const formData = new FormData();
    files.forEach((file: File) => {
      formData.append('files', file);
    });
    
    // Append user-uploaded policy files
    if (userUploadedPolicies && userUploadedPolicies.length > 0) {
      userUploadedPolicies.forEach((policy: UserUploadedPolicy) => {
        formData.append('policy_files', policy.file);
      });
    }
    
    // Append selected regulations as JSON string
    // Always send the array, even if empty, so backend knows user explicitly selected/deselected
    formData.append('selected_regulations', JSON.stringify(selectedRegulations || []));
    
    // Append custom names mapping for user-uploaded policies
    if (policyCustomNames && Object.keys(policyCustomNames).length > 0) {
      formData.append('policy_custom_names', JSON.stringify(policyCustomNames));
    }
    
    // Append custom columns if provided
    if (columns && columns.length > 0) {
      formData.append('custom_columns', JSON.stringify(columns));
    }
    
    // Append custom prompts if provided
    if (customPrompts) {
      formData.append('custom_system_prompt', customPrompts.systemPrompt);
    }

    // Track if we've already shown consolidated steps
    let uploadingStepShown = false;
    let parsingStepShown = false;

    const handler = new StreamHandler<ProcessingEvent>({
      url: getUrl('/api/compliance/upload'),
      method: 'POST',
      body: formData,
      onError: (error) => {
        console.error('Stream error:', error);
        addProcessingStep(`Error: ${error.message}`);
      }
    });

    handler
      .on('uploading', () => {
        if (!uploadingStepShown) {
          addProcessingStep('Uploading files...');
          uploadingStepShown = true;
        }
      })
      .on('parsing', () => {
        if (!parsingStepShown) {
          addProcessingStep('Parsing files...');
          parsingStepShown = true;
        }
      })
      .on('validating', () => {
        addProcessingStep('Validating file relevance...');
      })
      .on('verifying', (event) => {
        // Add step with regulation_index for precise matching
        setProcessingSteps(prev => [...prev, {
          id: `${Date.now()}-${Math.random()}`,
          message: `${event.data.regulation_index}/${event.data.total_regulations} - Verifying against ${event.data.regulation_name}...`,
          timestamp: Date.now(),
          regulationIndex: event.data.regulation_index,
          isComplete: false
        }]);
        setHasStartedVerification(true);
      })
      .on('regulation_complete', (event) => {
        // Update the processing step to show completion using regulation_index for precise matching
        setProcessingSteps(prev => {
          const updated = prev.map(step => {
            // Match by regulation_index for precise identification
            if (step.regulationIndex === event.data.regulation_index && !step.isComplete) {
              return {
                ...step,
                message: `${event.data.regulation_index}/${event.data.total_regulations} - Completed ${event.data.regulation_name}`,
                isComplete: true
              };
            }
            return step;
          });
          return updated;
        });
      })
      .on('issues_delta', (event) => {
        // Add issues incrementally as they arrive
        setComplianceIssues(prev => [...prev, ...event.data.issues]);
        // Switch to split view on first issues
        setHasStartedVerification(true);
        setShowProcessingSidebar(true);
      })
      .on('complete', () => {
        addProcessingStep('Verification complete');
        setValidFilesProcessingComplete(true);
        setIsSidebarMinimized(true);
        // Don't hide sidebar in invalid state - keep it visible
        // Only hide sidebar if we're transitioning to results from processing state
        setState(prevState => {
          if (prevState === 'processing') {
            setShowProcessingSidebar(false);
            return 'results';
          }
          return prevState;
        });
      })
      .on('document_invalid', (event) => {
        addProcessingStep(`Invalid file: ${event.data.filename}`);
        // Accumulate invalid files instead of replacing
        setInvalidFiles(prev => [...prev, { filename: event.data.filename, reason: event.data.reason }]);
        setState(prevState => prevState === 'processing' ? 'invalid' : prevState);
        // Show sidebar when we have invalid files
        setShowProcessingSidebar(true);
      })
      .on('file_validated', (event) => {
        addProcessingStep(`Valid file: ${event.data.filename}`);
        setValidFiles(prev => [...prev, event.data.filename]);
        setHasValidFilesProcessing(true);
        // Don't show sidebar yet - wait until verification actually starts
        // This prevents showing ComplianceTable during validation phase
      })
      .on('error', (event) => {
        addProcessingStep(`Error: ${event.data.message}`);
      });

    streamHandlerRef.current = handler;
    await handler.start();
  }, [addProcessingStep]);

  const handleWizardCancel = useCallback(() => {
    // Return to home screen when wizard is cancelled
    setState('home');
  }, []);

  const handleStartWizard = useCallback(() => {
    setState('wizard');
  }, []);

  const handleShowResults = useCallback(() => {
    setShowProcessingSidebar(true);
    setIsSidebarMinimized(false);
    setState('results');
  }, []);


  return (
    <PageLayout>
      {state === 'home' && (
        <div className="flex flex-col items-center justify-center flex-1 px-8 py-16">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-extrabold text-gray-900 mb-3">
              Compliance Checker Agent
            </h1>
            <p className="text-gray-500 text-lg">
              Hello there! Upload your documents and I'll check them for compliance with the policies you choose.
            </p>
          </div>
          <button
            onClick={handleStartWizard}
            className="px-8 py-3 bg-primary text-white text-lg font-semibold rounded-lg hover:bg-primary/90 transition-colors shadow-lg hover:shadow-xl"
          >
            Start
          </button>
        </div>
      )}
      {state === 'wizard' && (
        <ComplianceWizardModal 
          onComplete={handleWizardComplete} 
          onCancel={handleWizardCancel}
        />
      )}
      {state === 'processing' && !showProcessingSidebar && (
        <ProcessingView steps={processingSteps} />
      )}
      {state === 'processing' && showProcessingSidebar && hasStartedVerification && (
        <div className="flex flex-1 gap-6 overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <ComplianceTable issues={complianceIssues} isGenerating={true} columns={customColumns} />
          </div>
          <div className={`flex-shrink-0 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden transition-all duration-300 sticky top-6 self-start flex flex-col ${
            isSidebarMinimized ? 'w-12' : 'w-80'
          }`} style={{ maxHeight: 'calc(100vh - 3rem)' }}>
            <div className="flex items-center justify-between p-4 border-b border-gray-200 flex-shrink-0">
              {!isSidebarMinimized && (
                <h3 className="text-sm font-semibold text-gray-700">Processing Status</h3>
              )}
              <button
                onClick={() => setIsSidebarMinimized(!isSidebarMinimized)}
                className="p-1 hover:bg-gray-100 rounded transition-colors ml-auto"
                aria-label={isSidebarMinimized ? 'Expand sidebar' : 'Minimize sidebar'}
              >
                {isSidebarMinimized ? (
                  <MdChevronLeft className="w-5 h-5 text-gray-600" />
                ) : (
                  <MdChevronRight className="w-5 h-5 text-gray-600" />
                )}
              </button>
            </div>
            {!isSidebarMinimized && (
              <div className="p-4 overflow-hidden flex flex-col flex-1 min-h-0">
                <div className="flex flex-col gap-1 overflow-y-auto pr-2 flex-1">
                  {processingSteps.map((step, index) => {
                    // Determine if step should be active
                    let isActive = false;
                    if (step.regulationIndex !== undefined) {
                      // Regulation step: active if not complete
                      isActive = !step.isComplete && !validFilesProcessingComplete;
                    } else {
                      // Non-regulation step: active if it's the last step
                      // (and there are no incomplete regulation steps after it)
                      if (index === processingSteps.length - 1) {
                        isActive = !validFilesProcessingComplete;
                      } else {
                        // Check if there are any incomplete regulation steps after this non-regulation step
                        const hasIncompleteRegulationStepsAfter = processingSteps
                          .slice(index + 1)
                          .some(s => s.regulationIndex !== undefined && !s.isComplete);
                        // If there are incomplete regulation steps after, this non-regulation step is done
                        isActive = !hasIncompleteRegulationStepsAfter && !validFilesProcessingComplete;
                      }
                    }
                    return (
                      <ProcessingStep
                        key={step.id}
                        message={step.message}
                        isActive={isActive}
                      />
                    );
                  })}
                </div>
              </div>
            )}
            {isSidebarMinimized && (
              <div className="flex flex-col items-center py-4 gap-2">
                {processingSteps.slice(-3).map((step, index, arr) => {
                  // Determine if step should be active (for minimized view)
                  let isActive = false;
                  if (step.regulationIndex !== undefined) {
                    // Regulation step: active if not complete
                    isActive = !step.isComplete && !validFilesProcessingComplete;
                  } else {
                    // Non-regulation step: active if it's the last step in the visible slice
                    // (and there are no incomplete regulation steps after it)
                    if (index === arr.length - 1) {
                      isActive = !validFilesProcessingComplete;
                    } else {
                      // Check if there are any incomplete regulation steps after this non-regulation step
                      const hasIncompleteRegulationStepsAfter = arr
                        .slice(index + 1)
                        .some(s => s.regulationIndex !== undefined && !s.isComplete);
                      isActive = !hasIncompleteRegulationStepsAfter && !validFilesProcessingComplete;
                    }
                  }
                  return (
                    <div
                      key={step.id}
                      className={`w-2 h-2 rounded-full ${
                        isActive ? 'bg-primary animate-pulse' : 'bg-green-600'
                      }`}
                    />
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
      {state === 'results' && !showProcessingSidebar && (
        <ComplianceTable 
          issues={complianceIssues} 
          isGenerating={false} 
          onTryDifferentFile={handleResetToHome}
          columns={customColumns}
        />
      )}
      {state === 'results' && showProcessingSidebar && (
        <div className="flex flex-1 gap-6 overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <ComplianceTable 
              issues={complianceIssues} 
              isGenerating={false} 
              onTryDifferentFile={handleResetToHome}
              columns={customColumns}
            />
          </div>
          <div className={`flex-shrink-0 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden transition-all duration-300 sticky top-6 self-start ${
            isSidebarMinimized ? 'w-12' : 'w-80'
          }`}>
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              {!isSidebarMinimized && (
                <h3 className="text-sm font-semibold text-gray-700">Processing Status</h3>
              )}
              <button
                onClick={() => setIsSidebarMinimized(!isSidebarMinimized)}
                className="p-1 hover:bg-gray-100 rounded transition-colors ml-auto"
                aria-label={isSidebarMinimized ? 'Expand sidebar' : 'Minimize sidebar'}
              >
                {isSidebarMinimized ? (
                  <MdChevronLeft className="w-5 h-5 text-gray-600" />
                ) : (
                  <MdChevronRight className="w-5 h-5 text-gray-600" />
                )}
              </button>
            </div>
            {!isSidebarMinimized && (
              <div className="p-4 overflow-hidden">
                <div className="flex flex-col gap-1">
                  {processingSteps.slice(-8).map((step, index, arr) => (
                    <ProcessingStep
                      key={step.id}
                      message={step.message}
                      isActive={index === arr.length - 1 && !validFilesProcessingComplete}
                    />
                  ))}
                </div>
              </div>
            )}
            {isSidebarMinimized && (
              <div className="flex flex-col items-center py-4 gap-2">
                {processingSteps.slice(-3).map((step, index, arr) => (
                  <div
                    key={step.id}
                    className={`w-2 h-2 rounded-full ${
                      index === arr.length - 1 && !validFilesProcessingComplete ? 'bg-primary animate-pulse' : 'bg-green-600'
                    }`}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      {state === 'invalid' && !showProcessingSidebar && (
        <div className="flex flex-1 gap-6 overflow-hidden px-8 pt-4 pb-14">
          <div className="flex-1 overflow-y-auto">
            <InvalidDocumentView 
              invalidFiles={invalidFiles}
              onTryDifferentFile={handleResetToHome}
            />
          </div>
          {hasValidFilesProcessing && validFiles.length > 0 && (
            <div className="flex-1 overflow-y-auto">
              <ValidFilesSection
                validFiles={validFiles}
                isProcessing={!validFilesProcessingComplete}
                hasIssues={complianceIssues.length > 0}
                onVerifyFiles={handleShowResults}
              />
            </div>
          )}
        </div>
      )}
      {state === 'invalid' && showProcessingSidebar && (
        <div className="flex flex-1 gap-6 overflow-hidden px-8 pt-4 pb-14">
          <div className="flex-1 overflow-hidden flex flex-col gap-6">
            <div className="flex gap-6 flex-1 min-h-0">
              <div className="flex-1 overflow-y-auto">
                <InvalidDocumentView 
                  invalidFiles={invalidFiles}
                  onTryDifferentFile={handleResetToHome}
                />
              </div>
              {hasValidFilesProcessing && validFiles.length > 0 && (
                <div className="flex-1 overflow-y-auto">
                  <ValidFilesSection
                    validFiles={validFiles}
                    isProcessing={!validFilesProcessingComplete}
                    hasIssues={complianceIssues.length > 0}
                    onVerifyFiles={handleShowResults}
                  />
                </div>
              )}
            </div>
          </div>
          <div className={`flex-shrink-0 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden transition-all duration-300 sticky top-6 self-start flex flex-col ${
            isSidebarMinimized ? 'w-12' : 'w-80'
          }`} style={{ maxHeight: 'calc(100vh - 3rem)' }}>
            <div className="flex items-center justify-between p-4 border-b border-gray-200 flex-shrink-0">
              {!isSidebarMinimized && (
                <h3 className="text-sm font-semibold text-gray-700">Processing Status</h3>
              )}
              <button
                onClick={() => setIsSidebarMinimized(!isSidebarMinimized)}
                className="p-1 hover:bg-gray-100 rounded transition-colors ml-auto"
                aria-label={isSidebarMinimized ? 'Expand sidebar' : 'Minimize sidebar'}
              >
                {isSidebarMinimized ? (
                  <MdChevronLeft className="w-5 h-5 text-gray-600" />
                ) : (
                  <MdChevronRight className="w-5 h-5 text-gray-600" />
                )}
              </button>
            </div>
            {!isSidebarMinimized && (
              <div className="p-4 overflow-hidden flex flex-col flex-1 min-h-0">
                <div className="flex flex-col gap-1 overflow-y-auto pr-2 flex-1">
                  {processingSteps.map((step, index) => {
                    // Determine if step should be active
                    let isActive = false;
                    if (step.regulationIndex !== undefined) {
                      // Regulation step: active if not complete
                      isActive = !step.isComplete && !validFilesProcessingComplete;
                    } else {
                      // Non-regulation step: active if it's the last step
                      // (and there are no incomplete regulation steps after it)
                      if (index === processingSteps.length - 1) {
                        isActive = !validFilesProcessingComplete;
                      } else {
                        // Check if there are any incomplete regulation steps after this non-regulation step
                        const hasIncompleteRegulationStepsAfter = processingSteps
                          .slice(index + 1)
                          .some(s => s.regulationIndex !== undefined && !s.isComplete);
                        // If there are incomplete regulation steps after, this non-regulation step is done
                        isActive = !hasIncompleteRegulationStepsAfter && !validFilesProcessingComplete;
                      }
                    }
                    return (
                      <ProcessingStep
                        key={step.id}
                        message={step.message}
                        isActive={isActive}
                      />
                    );
                  })}
                </div>
              </div>
            )}
            {isSidebarMinimized && (
              <div className="flex flex-col items-center py-4 gap-2">
                {processingSteps.slice(-3).map((step, index, arr) => {
                  // Determine if step should be active (for minimized view)
                  let isActive = false;
                  if (step.regulationIndex !== undefined) {
                    // Regulation step: active if not complete
                    isActive = !step.isComplete && !validFilesProcessingComplete;
                  } else {
                    // Non-regulation step: active if it's the last step in the visible slice
                    // (and there are no incomplete regulation steps after it)
                    if (index === arr.length - 1) {
                      isActive = !validFilesProcessingComplete;
                    } else {
                      // Check if there are any incomplete regulation steps after this non-regulation step
                      const hasIncompleteRegulationStepsAfter = arr
                        .slice(index + 1)
                        .some(s => s.regulationIndex !== undefined && !s.isComplete);
                      isActive = !hasIncompleteRegulationStepsAfter && !validFilesProcessingComplete;
                    }
                  }
                  return (
                    <div
                      key={step.id}
                      className={`w-2 h-2 rounded-full ${
                        isActive ? 'bg-primary animate-pulse' : 'bg-green-600'
                      }`}
                    />
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </PageLayout>
  );
}

export default App;
