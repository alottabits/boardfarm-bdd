#!/usr/bin/env node
/**
 * Patch GenieACS to conditionally include TargetFileName in Download RPC
 * Only includes TargetFileName when it has a non-empty value
 * 
 * This patch fixes PrplOS compatibility issue where empty TargetFileName
 * causes Download RPC rejection. After this patch, GenieACS will omit
 * TargetFileName from TR-069 XML when it's empty/null, making it compatible
 * with PrplOS which rejects empty TargetFileName parameters.
 */

const fs = require('fs');
const path = '/opt/genieacs/dist/bin/genieacs-cwmp';

try {
    let code = fs.readFileSync(path, 'utf8');
    let modified = false;
    
    // Pattern 1: Match the exact case"download" pattern with targetFileName||""
    // The minified code uses template literals with escaped backticks
    // Actual code: case"download":mn(e,`task_${a._id}`,[["download",a.fileType,a.fileName,a.targetFileName||""]]);break;
    const pattern1 = /case"download":mn\(e,`task_\$\{a\._id\}`,\[\["download",a\.fileType,a\.fileName,a\.targetFileName\|\|""\]\]\);break;/g;
    const replacement1 = 'case"download":mn(e,`task_${a._id}`,[["download",a.fileType,a.fileName,a.targetFileName&&a.targetFileName.length>0?a.targetFileName:null]]);break;';
    
    // Pattern 2: More flexible - match targetFileName||"" in download array context
    // This handles variations in code minification where spacing might differ
    const pattern2 = /(\["download",a\.fileType,a\.fileName,)a\.targetFileName\|\|""(\]\))/g;
    const replacement2 = '$1(a.targetFileName&&a.targetFileName.length>0?a.targetFileName:null)$2';
    
    // Pattern 3: Even more flexible - matches any occurrence of targetFileName||"" near download
    const pattern3 = /(case"download"[^}]*?)a\.targetFileName\|\|""/g;
    const replacement3 = '$1(a.targetFileName&&a.targetFileName.length>0?a.targetFileName:null)';
    
    // Try patterns in order of specificity
    // Note: Don't use .test() before .replace() as it advances regex index
    // Instead, try replace and check if it changed anything
    const originalCode = code;
    
    // Pattern 1: Exact match
    code = code.replace(pattern1, replacement1);
    if (code !== originalCode) {
        modified = true;
        console.log('Applied patch pattern 1 (exact match)');
    } else {
        // Pattern 2: Flexible match
        code = code.replace(pattern2, replacement2);
        if (code !== originalCode) {
            modified = true;
            console.log('Applied patch pattern 2 (flexible match)');
        } else {
            // Pattern 3: Broad match
            code = code.replace(pattern3, replacement3);
            if (code !== originalCode) {
                modified = true;
                console.log('Applied patch pattern 3 (broad match)');
            } else {
                console.error('ERROR: Could not find Download RPC pattern to patch');
                console.error('The GenieACS code structure may have changed');
                console.error('Please verify the code structure in /opt/genieacs/dist/bin/genieacs-cwmp');
                process.exit(1);
            }
        }
    }
    
    if (modified) {
        fs.writeFileSync(path, code, 'utf8');
        console.log('Successfully patched GenieACS task creation to conditionally include TargetFileName');
    }
    
    // Also patch the provision function that generates Downloads instances
    // Pattern: const n=[`FileType:...`,`FileName:...`,`TargetFileName:...`].join(",");
    // Replace with conditional inclusion of TargetFileName
    const provisionPattern = /const n=\[`FileType:\$\{JSON\.stringify\(t\[1\]\|\|""\)\}`,`FileName:\$\{JSON\.stringify\(t\[2\]\|\|""\)\}`,`TargetFileName:\$\{JSON\.stringify\(t\[3\]\|\|""\)\}`\]\.join\(","\);/g;
    const provisionReplacement = 'const n=[`FileType:${JSON.stringify(t[1]||"")}`,`FileName:${JSON.stringify(t[2]||"")}`].concat(t[3]&&t[3].length>0?[`TargetFileName:${JSON.stringify(t[3])}`]:[]).join(",");';
    
    const originalProvisionCode = code;
    code = code.replace(provisionPattern, provisionReplacement);
    if (code !== originalProvisionCode) {
        fs.writeFileSync(path, code, 'utf8');
        console.log('Successfully patched GenieACS provision function to conditionally include TargetFileName');
        modified = true;
    }
    
    if (modified) {
        console.log('TargetFileName will now only be sent when it has a non-empty value');
    }
} catch (error) {
    console.error('ERROR patching GenieACS:', error.message);
    if (error.code === 'ENOENT') {
        console.error('File not found:', path);
        console.error('Please verify GenieACS is installed correctly');
    }
    process.exit(1);
}

