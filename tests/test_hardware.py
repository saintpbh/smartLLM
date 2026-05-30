"""Unit tests for SMART LLM Reference-Scarce Programming Upgrade (Hardware/Bootstrap/Verify)."""

from __future__ import annotations

import unittest
import json
from pathlib import Path
from smart_llm.bootstrap import parse_c_header_defines, ingest_reference_material
from smart_llm.learn import record_lesson, compile_lessons_widget
from smart_llm.verify import scan_hardware_constraints, build_hardware_verify_widget

class TestHardwareUpgrade(unittest.TestCase):

    def test_bootstrap_c_header_parsing(self):
        """Test parsing of C/C++ header `#define` registers."""
        workspace = Path("/tmp/mock_hw_workspace")
        workspace.mkdir(exist_ok=True)
        
        # Write mock header file
        header_file = workspace / "stm32f4xx.h"
        header_file.write_text("""
#define GPIOA_MODER 0x40020000
#define GPIOB_OTYPER 0x40020404
#define RCC_AHB1ENR 0x40023830
        """, encoding="utf-8")
        
        # Parse registers
        regs = parse_c_header_defines(header_file)
        self.assertEqual(len(regs), 3)
        self.assertEqual(regs["GPIOA_MODER"], "0x40020000")
        self.assertEqual(regs["RCC_AHB1ENR"], "0x40023830")
        
        # Test ingestion
        res = ingest_reference_material(workspace, header_file)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["ingested_files"], 1)
        self.assertEqual(res["registers_count"], 3)
        
        # Clean up
        (workspace / "smart-llm-out" / "index.json").unlink()
        (workspace / "smart-llm-out").rmdir()
        header_file.unlink()
        workspace.rmdir()

    def test_lesson_recording_and_compilation(self):
        """Test recording of post-mortem lessons and rules compilation."""
        workspace = Path("/tmp/mock_lesson_workspace")
        workspace.mkdir(exist_ok=True)
        
        # Record lesson
        res = record_lesson(
            workspace,
            "GPIO pull-up resistor setup was missing on high-speed pin",
            "Set PUPDR to GPIO_PULLUP (0x01) on high-speed GPIO Pin A5",
            "gpio, stm32, pullup"
        )
        self.assertEqual(res["status"], "success")
        
        # Compile widget
        widget = compile_lessons_widget(workspace)
        self.assertIn("HARD-LEARNED LESSONS", widget)
        self.assertIn("GPIO pull-up resistor setup was", widget)
        self.assertIn("GPIO_PULLUP", widget)
        
        # Clean up
        for f in (workspace / "lessons").glob("*"):
            f.unlink()
        (workspace / "lessons").rmdir()
        workspace.rmdir()

    def test_hardware_constraint_checks(self):
        """Test static detection of pin boundaries and register mismatches."""
        workspace = Path("/tmp/mock_verify_workspace")
        workspace.mkdir(exist_ok=True)
        
        # Create a mock index.json with register map
        out_dir = workspace / "smart-llm-out"
        out_dir.mkdir(exist_ok=True)
        index_file = out_dir / "index.json"
        
        index_data = {
            "doc_map": {},
            "register_map": {
                "GPIOA_MODER": "0x40020000",
                "RCC_AHB1ENR": "0x40023830"
            }
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f)
            
        # Create mock C source file with intentional hardware violations:
        # 1. GPIO_PIN_16 (Standard STM32 GPIO is 0-15, 16 is out of bounds)
        # 2. Unregistered GPIO_DUMMY_REG (not in register_map)
        c_src = workspace / "main.c"
        c_src.write_text("""
void SystemInit(void) {
    RCC_AHB1ENR = 0x01; // Valid register
    GPIO_DUMMY_REG = 0x99; // Invalid/unrecognized register!
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_16, GPIO_PIN_SET); // Invalid Pin 16!
}
        """, encoding="utf-8")
        
        # Run verify
        violations = scan_hardware_constraints(workspace)
        self.assertEqual(len(violations), 2)
        
        # Verify specific errors
        errors = [v["error_type"] for v in violations]
        self.assertIn("GPIO Pin Out of Bounds (GPIO 핀 범위 초과)", errors)
        self.assertIn("Unresolved Register Definition (정의되지 않은 레지스터 참조)", errors)
        
        # Test widget compiler
        widget = build_hardware_verify_widget(violations)
        self.assertIn("GPIO Pin Out of Bounds", widget)
        self.assertIn("GPIO_DUMMY_REG", widget)
        
        # Clean up
        c_src.unlink()
        index_file.unlink()
        out_dir.rmdir()
        workspace.rmdir()

if __name__ == "__main__":
    unittest.main()
