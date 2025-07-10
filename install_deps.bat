@echo off
echo Installing Su Tools Dependencies...
echo.

echo Installing core dependencies...
pip install pyinstaller pillow pywin32

echo.
echo Installing OpenAI dependency for Su_Chat...
pip install openai

echo.
echo Installing automation dependencies for Su_Click...
pip install mouse keyboard

echo.
echo Installation complete!
echo.
echo You can now run the applications:
echo   - Su_Onefile_Builder: cd onefile && python onefile.pyw
echo   - Su_Chat: cd su_chat && python su_chat.pyw  
echo   - Su_Click: cd su_click && python su_click.pyw
echo.
pause