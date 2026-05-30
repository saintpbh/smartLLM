"""Stage 3: Pre-emptive Hardware / AST Constraint Verification."""

from __future__ import annotations

import re
import json
from pathlib import Path

def scan_hardware_constraints(workspace_path: Path) -> list[dict]:
    """Analyze C/C++ code against parsed registers and pins, flagging potential violations."""
    workspace_path = Path(workspace_path).resolve()
    index_file = workspace_path / "smart-llm-out" / "index.json"
    
    # 1. Load the register map compiled in Stage 1
    register_map = {}
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
                register_map = index_data.get("register_map", {})
        except Exception:
            pass
            
    from smart_llm.detect import detect_files
    scan_res = detect_files(workspace_path)
    
    c_files = [
        workspace_path / f 
        for f in scan_res["files"]["code"] 
        if f.endswith((".c", ".cpp", ".cc", ".h", ".hpp"))
    ]
    
    violations = []
    
    # Patterns to match hardware symbols
    pin_pattern = re.compile(r"GPIO_PIN_(\d+)")
    # Identifiers starting with hardware domains like GPIO_, RCC_, USART_, TIM_, ADC_
    hw_symbol_pattern = re.compile(r"\b((?:GPIO|RCC|USART|TIM|ADC|SPI|HAL)_[\w_]+)\b")
    
    for file_path in c_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
            
        # Find all local definitions in the same file to prevent false positives
        local_defines = set(re.findall(r"#\s*define\s+([\w_]+)", content))
        local_functions = set(re.findall(r"\b([\w_]+)\s*\([^)]*\)\s*\{", content))
        
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            line_no = idx + 1
            
            # 1. Validate GPIO Pin boundaries (Standard GPIO_PIN_0 to GPIO_PIN_15)
            pin_matches = pin_pattern.findall(line)
            for pin_str in pin_matches:
                pin_num = int(pin_str)
                if pin_num > 15:
                    violations.append({
                        "file": str(file_path.relative_to(workspace_path)),
                        "line": line_no,
                        "symbol": f"GPIO_PIN_{pin_num}",
                        "error_type": "GPIO Pin Out of Bounds (GPIO 핀 범위 초과)",
                        "guideline": f"STM32 표준 GPIO 핀 범위는 0~15입니다. 핀 번호 {pin_num}은 물리적으로 존재하지 않습니다."
                    })
                    
            # 2. Check for unrecognized register or macro symbols
            hw_matches = hw_symbol_pattern.findall(line)
            for sym in hw_matches:
                # If it's a standard keyword or locally defined symbol, skip it
                if sym in local_defines or sym in local_functions:
                    continue
                    
                # Skip highly common HAL standard functions and standard PIN constants
                if (sym.startswith("HAL_GPIO_") or 
                    sym.startswith("HAL_Delay") or 
                    sym.startswith("HAL_Init") or 
                    sym.startswith("GPIO_PIN_")):
                    continue
                    
                # If we have a reference register map, and this symbol starts with typical register domains, check it
                if register_map and any(prefix in sym for prefix in ("GPIO", "RCC", "USART", "TIM")):
                    if sym not in register_map:
                        violations.append({
                            "file": str(file_path.relative_to(workspace_path)),
                            "line": line_no,
                            "symbol": sym,
                            "error_type": "Unresolved Register Definition (정의되지 않은 레지스터 참조)",
                            "guideline": f"레지스터 `{sym}`은(는) 가져온 데이터시트/헤더 명세에 존재하지 않습니다. 주소 오타를 확인하거나 Stage 1에서 데이터시트를 먼저 임포트하십시오."
                        })
                        
    return violations


def build_hardware_verify_widget(violations: list[dict]) -> str:
    """Compile hardware violation alerts into a premium alert widget for AGENTS.md."""
    if not violations:
        return ""
        
    lines = [
        "## 🔌 [HARDWARE AST STATIC CONSTRAINT WARNING] 🔌",
        "*경고: C/C++ 하드웨어 제어 코드에서 레지스터 오타 또는 하드웨어 물리적 범위 초과 오류가 감지되었습니다. 에이전트들은 다음 불일치를 컴파일 전에 즉시 해결하십시오.*",
        ""
    ]
    
    for v in violations:
        lines.append(
            f"### 🛑 Hardware Conflict: `{v['symbol']}`\n"
            f"- **오류 타입**: `{v['error_type']}`\n"
            f"- **발생 위치**: `{v['file']}` (L{v['line']})\n"
            f"- **조치 가이드**: {v['guideline']}\n"
        )
        
    lines.append("")
    return "\n".join(lines)
