import os
import glob
import re
import subprocess
import shutil
from datetime import datetime
import win32com.client as win32
from win32com.client import constants

# Configuration
TARGET_DIR        = r'D:\Temp'
FILE_PREFIX       = 'heis*'
SOURCE_SHEET = '4. 알람 설비 태그'
TARGET_SHEET = '5. 알람 설비 대상 정보'

HEADER_ROW   = 1
TARGET_SHEET_TEMPLATE_ROW = 2
TARGET_SHEET_START_ROW    = 3

HEADER_MAP = {
    'TAG_ID': ('태그 아이디',),
    'ALARM_KO_NAME': ('알람 한글명', '태그 한글명'),
    'ALARM_EN_NAME': ('알람 영문명', '태그 영문명'),
}

def log(msg, t0=None):
    """Log messages with timestamp"""
    now = datetime.now().strftime('%m-%d %H:%M:%S')
    if t0:
        elapsed = (datetime.now() - t0).total_seconds()
        print(f'[{now}] {msg} (elapsed {elapsed:.2f}s)')
    else:
        print(f'[{now}] {msg}')

def kill_excel():
    """Kill any running Excel processes"""
    try:
        subprocess.call(['taskkill', '/f', '/im', 'EXCEL.EXE'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

def normalize_text(text):
    """Remove line breaks and normalize text"""
    if not text:
        return ''
    # Remove line breaks and extra whitespace
    normalized = re.sub(r'\s+', ' ', str(text).strip())
    return normalized

def normalize_header(text):
    """Normalize headers for matching (remove special chars, lowercase)"""
    return re.sub(r'[^\w가-힣]', '', str(text or '')).lower()

def normalize_sheet_name(name):
    """Normalize sheet names for comparison"""
    return re.sub(r'[^\w가-힣.]', '', str(name or '')).lower()

def find_latest_revision(directory, prefix):
    """Find the latest revision of a file."""
    pattern = os.path.join(directory, f"{prefix}*.xlsx")
    files = glob.glob(pattern)

    latest_file = None
    latest_rev = -1

    for f in files:
        rev_match = re.search(r'_rev(\d+)', f)
        if rev_match:
            rev_num = int(rev_match.group(1))
            if rev_num > latest_rev:
                latest_rev = rev_num
                latest_file = f

    if latest_file:
        return latest_file, latest_rev

    # If no revisioned file, find the base file
    base_files = [f for f in files if '_rev' not in f]
    if base_files:
        return base_files[0], 0

    return None, -1

def create_new_revision(filepath, rev_num):
    """Create a new revision of the file."""
    dir_name = os.path.dirname(filepath)
    base_name = os.path.basename(filepath)
    name, ext = os.path.splitext(base_name)
    
    # Remove existing revision suffix if present
    name = re.sub(r'_rev\d+', '', name)
    
    new_rev_name = f"{name}_rev{rev_num + 1:02d}{ext}"
    new_filepath = os.path.join(dir_name, new_rev_name)
    
    shutil.copy2(filepath, new_filepath)
    log(f'Created revision file: {os.path.basename(new_filepath)}')
    return new_filepath

def find_header_columns(sheet, header_map):
    """Find column positions for headers based on HEADER_MAP"""
    column_map = {}
    
    if not sheet:
        return column_map
    
    try:
        last_col = sheet.UsedRange.Columns.Count
    except:
        return column_map
    
    # Get all headers from row 1
    headers = {}
    for col in range(1, last_col + 1):
        try:
            cell_value = sheet.Cells(HEADER_ROW, col).Value
            if cell_value:
                normalized = normalize_header(cell_value)
                headers[normalized] = col
        except:
            continue
    
    # Map headers using HEADER_MAP
    for key, possible_names in header_map.items():
        for name in possible_names:
            normalized_name = normalize_header(name)
            if normalized_name in headers:
                column_map[key] = headers[normalized_name]
                break
    
    return column_map

def count_source_rows(sheet):
    """Count how many data rows are in the source sheet"""
    if not sheet:
        return 0
    
    try:
        # Find last row with data in column A
        last_row = sheet.Cells(sheet.Rows.Count, 1).End(constants.xlUp).Row
        # Data rows start after header row
        data_rows = max(0, last_row - HEADER_ROW)
        return data_rows
    except:
        return 0

def copy_template_formatting(target_sheet, num_rows):
    """Copy template row formatting to all data rows"""
    if not target_sheet or num_rows <= 0:
        return
    
    try:
        # Copy template row
        template_row = target_sheet.Rows(TARGET_SHEET_TEMPLATE_ROW)
        template_row.Copy()
        
        # Insert new rows starting from TARGET_SHEET_START_ROW
        target_range = target_sheet.Rows(TARGET_SHEET_START_ROW).Resize(num_rows)
        target_range.Insert(Shift=constants.xlDown, CopyOrigin=constants.xlFormatFromLeftOrAbove)
        
        # Clear clipboard
        target_sheet.Application.CutCopyMode = False
        
        log(f'Filled down template formatting for {num_rows} rows')
        
    except Exception as e:
        log(f'Error copying template formatting: {str(e)}')

def copy_formulas_and_values(target_sheet, num_rows):
    """Copy formulas and static values from template row"""
    if not target_sheet or num_rows <= 0:
        return
    
    try:
        last_col = target_sheet.UsedRange.Columns.Count
        
        for col in range(1, last_col + 1):
            template_cell = target_sheet.Cells(TARGET_SHEET_TEMPLATE_ROW, col)
            
            # Define the range for copying
            start_row = TARGET_SHEET_START_ROW
            end_row = TARGET_SHEET_START_ROW + num_rows - 1
            target_range = target_sheet.Range(
                target_sheet.Cells(start_row, col),
                target_sheet.Cells(end_row, col)
            )
            
            if template_cell.HasFormula:
                # Copy formula and let Excel adjust references
                template_cell.Copy()
                target_range.PasteSpecial(Paste=constants.xlPasteFormulas)
            else:
                # Copy static value
                value = template_cell.Value
                if value is not None:
                    target_range.Value = value
        
        # Clear clipboard
        target_sheet.Application.CutCopyMode = False
        log('Copied formulas and static values from template row')
        
    except Exception as e:
        log(f'Error copying formulas and values: {str(e)}')

def copy_data_values(source_sheet, target_sheet, source_cols, target_cols, num_rows):
    """Copy data values from source to target sheet using column mappings"""
    if not source_sheet or not target_sheet or num_rows <= 0:
        return
    
    copied_columns = 0
    
    for key in HEADER_MAP.keys():
        source_col = source_cols.get(key)
        target_col = target_cols.get(key)
        
        if source_col and target_col:
            try:
                # Source range (skip header row)
                source_range = source_sheet.Range(
                    source_sheet.Cells(HEADER_ROW + 1, source_col),
                    source_sheet.Cells(HEADER_ROW + num_rows, source_col)
                )
                
                # Target range
                target_range = target_sheet.Range(
                    target_sheet.Cells(TARGET_SHEET_START_ROW, target_col),
                    target_sheet.Cells(TARGET_SHEET_START_ROW + num_rows - 1, target_col)
                )
                
                # Get values and normalize text (remove line breaks)
                values = source_range.Value
                if values:
                    if isinstance(values, tuple):
                        # Multiple values
                        normalized_values = []
                        for row in values:
                            if isinstance(row, tuple):
                                normalized_values.append(tuple(normalize_text(cell) for cell in row))
                            else:
                                normalized_values.append((normalize_text(row),))
                        target_range.Value = normalized_values
                    else:
                        # Single value
                        target_range.Value = normalize_text(values)
                
                copied_columns += 1
                log(f'Copied column {key}: {source_col} -> {target_col}')
                
            except Exception as e:
                log(f'Error copying column {key}: {str(e)}')
    
    log(f'Successfully copied {copied_columns} columns of data')

def process_file(filepath, rev_num):
    """Process a single Excel file"""
    t0 = datetime.now()
    
    # Create a new revision for processing
    new_filepath = create_new_revision(filepath, rev_num)
    log(f'Processing {os.path.basename(new_filepath)}')
    
    # Initialize Excel
    xl = None
    try:
        xl = win32.gencache.EnsureDispatch('Excel.Application')
        xl.Visible = False
        xl.DisplayAlerts = False
        xl.ScreenUpdating = False
        xl.EnableEvents = False
        
        try:
            xl.Calculation = constants.xlCalculationManual
        except:
            log('Warning: Could not set calculation to manual')
        
        # Open workbook
        wb = xl.Workbooks.Open(new_filepath)
        
        # Find sheets by normalized names
        source_sheet = None
        target_sheet = None
        
        for sheet in wb.Sheets:
            normalized_name = normalize_sheet_name(sheet.Name)
            if normalize_sheet_name(SOURCE_SHEET) in normalized_name:
                source_sheet = sheet
            elif normalize_sheet_name(TARGET_SHEET) in normalized_name:
                target_sheet = sheet
        
        if not source_sheet:
            log(f'Error: Source sheet "{SOURCE_SHEET}" not found')
            return
        
        if not target_sheet:
            log(f'Error: Target sheet "{TARGET_SHEET}" not found')
            return
        
        log(f'Found source sheet: {source_sheet.Name}')
        log(f'Found target sheet: {target_sheet.Name}')
        
        # Step 1: Count rows in source sheet
        num_rows = count_source_rows(source_sheet)
        log(f'Found {num_rows} data rows in source sheet', t0)
        
        if num_rows <= 0:
            log('No data rows found in source sheet')
            return
        
        # Clear existing data in target sheet (but keep template row)
        try:
            last_row = target_sheet.Cells(target_sheet.Rows.Count, 1).End(constants.xlUp).Row
            if last_row >= TARGET_SHEET_START_ROW:
                clear_range = target_sheet.Range(
                    target_sheet.Rows(TARGET_SHEET_START_ROW),
                    target_sheet.Rows(last_row)
                )
                clear_range.Delete(Shift=constants.xlUp)
                log(f'Cleared existing data rows {TARGET_SHEET_START_ROW} to {last_row}', t0)
        except:
            pass
        
        # Step 2: Fill down template row with full formatting
        copy_template_formatting(target_sheet, num_rows)
        copy_formulas_and_values(target_sheet, num_rows)
        
        # Step 3: Get header mappings and copy data
        source_columns = find_header_columns(source_sheet, HEADER_MAP)
        target_columns = find_header_columns(target_sheet, HEADER_MAP)
        
        log(f'Source columns: {source_columns}', t0)
        log(f'Target columns: {target_columns}', t0)
        
        # Copy data values using header mappings
        copy_data_values(source_sheet, target_sheet, source_columns, target_columns, num_rows)
        
        # Restore Excel settings
        try:
            xl.Calculation = constants.xlCalculationAutomatic
        except:
            pass
        xl.ScreenUpdating = True
        xl.EnableEvents = True
        
        # Save and close
        wb.Save()
        wb.Close(SaveChanges=True)
        
        log(f'Successfully processed {os.path.basename(filepath)}', t0)
        
    except Exception as e:
        log(f'Error processing file: {str(e)}')
    
    finally:
        if xl:
            try:
                xl.Quit()
            except:
                pass

def main():
    """Main function to process all matching files"""
    log('Starting heis 5sh processing...')
    
    # Kill any existing Excel processes
    kill_excel()
    
    # Find the latest revision
    latest_file, latest_rev = find_latest_revision(TARGET_DIR, FILE_PREFIX)
    
    if not latest_file:
        log(f'No files found with prefix "{FILE_PREFIX}" in {TARGET_DIR}')
        return
        
    log(f'Found latest revision: {os.path.basename(latest_file)} (rev {latest_rev})')

    # Process the latest file
    try:
        process_file(latest_file, latest_rev)
    except Exception as e:
        log(f'Error processing file {latest_file}: {str(e)}')
    
    log('All files processed')

if __name__ == '__main__':
    main()
