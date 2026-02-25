function macOneTime()
%MACONETIME Coach the user to allow MEX files on macOS.
%
%   pyraview.macOneTime()
%
%   This function guides the user through the process of allowing the
%   'pyraview.mex' binary to run on macOS, which often blocks it by
%   default as "unidentified developer" software.
%
%   This process only needs to be done once per installation/upgrade.

    if ~ismac
        disp('This function is intended for macOS users only.');
        return;
    end

    fprintf('----------------------------------------------------------------\n');
    fprintf('Pyraview macOS Security Check\n');
    fprintf('----------------------------------------------------------------\n');
    fprintf('macOS often blocks MEX files from running because they are not\n');
    fprintf('signed by an identified developer. You will likely see a popup\n');
    fprintf('saying "pyraview.mex" cannot be opened.\n\n');

    fprintf('INSTRUCTIONS:\n');
    fprintf('1. Open "System Settings" -> "Privacy & Security".\n');
    fprintf('2. Scroll down to the "Security" section.\n');
    fprintf('3. Look for a message saying "pyraview.mex" was blocked.\n');
    fprintf('4. Click "Allow Anyway" or "Open Anyway".\n');
    fprintf('   (You might need to click "Cancel" on the popup first).\n');
    fprintf('----------------------------------------------------------------\n');

    input('Press Enter to attempt running pyraview.pyraview...', 's');

    try
        % Call with no arguments to trigger "Usage" error from C code.
        % If the library is blocked, this call will throw a system error (e.g. Invalid MEX-file)
        % before executing the C code.
        pyraview.pyraview();
    catch ME
        % If it is the "InvalidInput" error from our C code, it loaded fine!
        if strcmp(ME.identifier, 'Pyraview:InvalidInput')
            fprintf('Success! pyraview.mex loaded successfully.\n');
        else
            fprintf('\nError: %s\n', ME.message);
            fprintf('It seems pyraview.mex was blocked or failed to load.\n');
            fprintf('Please go to System Settings -> Privacy & Security and allow it.\n');
            input('Press Enter after you have allowed the file...', 's');

            % Retry
            try
                pyraview.pyraview();
            catch ME2
                 if strcmp(ME2.identifier, 'Pyraview:InvalidInput')
                    fprintf('Success! pyraview.mex loaded successfully on retry.\n');
                 else
                    fprintf('Still failed: %s\n', ME2.message);
                    fprintf('You may need to try again manually.\n');
                 end
            end
        end
    end

    fprintf('\n----------------------------------------------------------------\n');
    fprintf('Security check complete. You should not need to do this again.\n');
end
