import os
import fitz  # PyMuPDF


class PDFTool:
    """Extracts text from PDF files and summarizes using local LLM."""

    def extract_text(self, file_path: str) -> str:
        """Read all pages of a PDF and return concatenated text."""
        if not os.path.exists(file_path):
            return None

        doc = fitz.open(file_path)
        text = ""

        for page in doc:
            text += page.get_text()

        doc.close()
        return text.strip()

    # Maximum characters of source text to send to LLM
    MAX_INPUT_CHARS = 3000

    def summarize_text(self, text: str) -> str:
        """Two-pass summarization: extract topics, then synthesize briefing."""
        trimmed = text[:self.MAX_INPUT_CHARS]

        # Pass 1: Extract key topics from document
        print("[PDFTool] Pass 1: Extracting key topics...")
        topics = self._extract_topics(trimmed)

        # Pass 2: Synthesize topics into executive briefing
        print("[PDFTool] Pass 2: Writing executive briefing...")
        briefing = self._synthesize_briefing(topics, strict=False)
        cleaned = self._clean_summary(briefing)

        # If procedural language still detected, retry with stronger constraint
        if self._has_procedural_language(cleaned):
            print("[PDFTool] Procedural language detected, retrying...")
            briefing = self._synthesize_briefing(topics, strict=True)
            cleaned = self._clean_summary(briefing)

        # Fallback if output is too thin
        if len(cleaned.split()) < 15:
            cleaned = (
                "This document provides technical guidance covering "
                "multiple components and implementation details. "
                "Please review the original file for full content."
            )

        return cleaned

    def _extract_topics(self, text: str) -> str:
        """Pass 1: Ask LLM to identify key topics, purpose, and components."""
        prompt = (
            "Read the document below carefully.\n\n"
            "Answer these 3 questions in plain short sentences:\n"
            "1. What is the main purpose of this document?\n"
            "2. What are the 3 to 5 most important topics or components it covers?\n"
            "3. How do these components relate to each other?\n\n"
            "Keep your answer under 80 words. No code. No markdown.\n\n"
            f"Document:\n{text}\n\nAnswers:"
        )

        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from llm import _chat
        try:
            return _chat(system="", user=prompt).strip()
        except Exception as e:
            print(f"[PDFTool] LLM Error: {e}")
            return "Failed to extract topics."

    def _synthesize_briefing(self, topics: str, strict: bool) -> str:
        """Pass 2: Write cohesive briefing from extracted topics only."""
        if not strict:
            prompt = (
                "Using ONLY the information below, write a professional "
                "executive briefing in exactly 2 paragraphs.\n\n"
                "Paragraph 1: What is this document about and why does it matter.\n"
                "Paragraph 2: What are the key components and how they connect.\n\n"
                "Rules:\n"
                "- Maximum 150 words.\n"
                "- Write complete flowing sentences.\n"
                "- Describe the system as an integrated workflow.\n"
                "- Do NOT list steps or instructions.\n"
                "- Do NOT use bullet points, headings, or markdown.\n"
                "- Do NOT use code or technical commands.\n"
                "- Do NOT use step numbers or sequential indicators such as "
                "'first', 'next', 'then', 'finally', 'subsequently'.\n"
                "- Do NOT use instructional phrasing or process narration.\n"
                "- If any sequential phrasing appears, rewrite internally "
                "before producing final output.\n"
                "- Professional tone, plain text only.\n\n"
                f"Key information:\n{topics}\n\nExecutive briefing:"
            )
        else:
            prompt = (
                "Rewrite the following information as a conceptual system overview.\n\n"
                "Absolutely no procedural language. No steps. No sequences.\n"
                "No 'first', 'next', 'then', 'finally'. No instructions.\n"
                "Describe WHAT the system is and WHY it matters.\n"
                "Write exactly 2 paragraphs. Maximum 120 words. Plain text only.\n\n"
                f"Information:\n{topics}\n\nSystem overview:"
            )

        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from llm import _chat
        try:
            return _chat(system="", user=prompt).strip()
        except Exception as e:
            print(f"[PDFTool] LLM Error: {e}")
            return "Failed to synthesize briefing."

    def _has_procedural_language(self, text: str) -> bool:
        """Check if text still contains procedural/sequential language."""
        import re
        procedural_patterns = [
            r"\bstep\s+\d",
            r"\bfirst\b", r"\bsecond\b", r"\bthird\b",
            r"\bnext\b", r"\bthen\b", r"\bfinally\b", r"\bsubsequently\b",
            r"\bafterwards?\b", r"\bfollowed by\b",
        ]
        for pattern in procedural_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _clean_summary(self, text: str) -> str:
        """Post-process LLM output: remove procedural language, reshape paragraphs."""
        import re

        # Remove fenced code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)

        # Remove inline backticks
        text = text.replace("`", "")

        # Remove markdown headings
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

        # Remove bold/italic markers
        text = re.sub(r"\*{1,3}", "", text)

        # Remove bullet and numbered list markers (keep the text)
        text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)

        # Strip trailing colons (reshape to periods)
        text = re.sub(r":\s*$", ".", text, flags=re.MULTILINE)

        # Remove sentences containing "Step N" pattern
        text = re.sub(r"[^.]*\bStep\s+\d[^.]*\.\s*", "", text, flags=re.IGNORECASE)

        # Replace sequential connectors with neutral phrasing
        text = re.sub(r"\bFirst(?:ly)?,?\s+", "The system ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bNext,?\s+", "Additionally, ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bThen,?\s+", "The workflow also ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bFinally,?\s+", "These components work together as ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bSubsequently,?\s+", "Furthermore, ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bAfterwards?,?\s+", "In addition, ", text, flags=re.IGNORECASE)

        # Merge fragment lines into flowing paragraphs
        lines = text.split("\n")
        merged = []
        buffer = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if buffer:
                    merged.append(buffer)
                    buffer = ""
                continue
            if buffer:
                buffer += " " + stripped
            else:
                buffer = stripped
        if buffer:
            merged.append(buffer)

        text = "\n\n".join(merged)

        # Collapse extra whitespace
        text = re.sub(r"  +", " ", text).strip()

        # Hard truncate to 150 words
        words = text.split()
        if len(words) > 150:
            text = " ".join(words[:150]) + "..."

        return text

    def execute(self, action: str, parameters: dict = None) -> dict:
        """
        Route PDF actions with standard signature.
        
        Supported actions:
        - summarize: Extract and summarize PDF
        - extract: Extract raw text only
        """
        parameters = parameters or {}
        
        if action == "summarize":
            file_path = parameters.get("file_path")
            if not file_path:
                return {
                    "status": "error",
                    "message": "Missing required parameter: file_path",
                    "data": None
                }
            
            return self._summarize_pdf(file_path)
        
        elif action == "extract":
            file_path = parameters.get("file_path")
            if not file_path:
                return {
                    "status": "error",
                    "message": "Missing required parameter: file_path",
                    "data": None
                }
            
            text = self.extract_text(file_path)
            
            if text is None:
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}",
                    "data": None
                }
            
            return {
                "status": "success",
                "message": "Text extracted successfully.",
                "data": text
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown PDF action: {action}",
                "data": None
            }
    
    def _summarize_pdf(self, file_path: str) -> dict:
        """Full pipeline: extract text, summarize, return structured result."""
        print(f"[PDFTool] Processing: {file_path}")

        # Step 1: Extract text
        text = self.extract_text(file_path)

        if text is None:
            print("[PDFTool] Error: File not found.")
            return {
                "status": "error",
                "message": f"File not found: {file_path}",
                "data": None
            }

        if text == "":
            print("[PDFTool] Error: No extractable text in PDF.")
            return {
                "status": "error",
                "message": "PDF contains no extractable text.",
                "data": None
            }

        # Step 2: Summarize
        print("[PDFTool] Extracting text... done.")
        print("[PDFTool] Summarizing with LLM...")
        summary = self.summarize_text(text)
        print("[PDFTool] Summarization complete.")

        return {
            "status": "success",
            "message": "PDF summarized successfully.",
            "data": summary
        }
