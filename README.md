# 🔍 CodeSmell Detector

An academic-grade, web-based automated **Code Smell Detection and Software Metrics Analysis Tool** for Java source code. 

Built on research from *"An automatic code smell detection plugin using code metrics analysis"* (Department of Computer Science and Engineering / IIT, University of Dhaka) and foundational object-oriented metric principles established by **Lanza & Marinescu** (*Object-Oriented Metrics in Practice*).

---

## 🚀 Key Features

- **⚡ Fast GitHub Repository Analysis**: Stream public GitHub repository archives directly into memory via zipball streaming without hitting GitHub API rate limits. Analyzes hundreds of Java files in seconds.
- **📦 Multi-File & ZIP Archive Upload**: Drag & drop individual `.java` files or nested `.zip` project archives. Supports automated package directory structure extraction.
- **✍️ Instant Code Analysis**: Direct paste editor for quick snippet analysis.
- **🖥️ IDE-like Dark Desktop Interface**: Full-featured single page application (SPA) featuring:
  - File tree explorer with smell count badges per file.
  - Multi-tab syntax-highlighted code editor with line-by-line smell markers.
  - Click-to-jump navigation from detected smell alerts directly to exact source lines.
  - Interactive Metrics Dashboard displaying project summaries, averages, smell distributions, and class/method metrics.
- **🔄 Session Management**: One-click **New Session** system button to clear active analyses and reset workspaces instantly.

---

## 🛠️ Architecture & Technical Design

### System Overview

```
                        ┌──────────────────────────────┐
                        │      Frontend (SPA UI)       │
                        │  Vanilla JS (ES6+) / HTML5   │
                        │     Dark VS Code Theme       │
                        └──────────────┬───────────────┘
                                       │  JSON / Multipart API
                                       ▼
                        ┌──────────────────────────────┐
                        │    Backend (Flask Server)    │
                        │        Python 3.8+           │
                        └──────────────┬───────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│        JavaParser AST        │              │       SmellDetector          │
│ - Lexical Comment Stripper   │              │ - 10 Detection Rules         │
│ - Regex Class/Method Parser  │─────────────►│ - Lanza-Marinescu Thresholds │
│ - Brace-Matching Scanner     │              │ - Severity Classification    │
│ - Metric Calculation Engine  │              └──────────────────────────────┘
└──────────────────────────────┘
```

### 1. Lexical Parsing (`java_parser.py`)
- **Comment Stripper**: Removes line (`//`) and block (`/* ... */`) comments while preserving newline positions so source code line numbers accurately map back to line markers.
- **Declaration Extraction**: Extracts class declarations, fields, methods, parameters, and modifiers using regex matching and brace-matching string scanners.
- **Cross-Reference Coupling Metrics**: Calculates inter-class coupling (`CINT`, `CDISP`, `ATFD`, `LAA`, `FDP`, `CM`, `CC`) by building a global invocation map across all classes in the project.

### 2. Smell Detection (`smell_detector.py`)
Applies formal quantitative metrics rules to evaluate candidate classes and methods against research-derived thresholds. Categorizes detected smells into `High` and `Medium` severity levels.

---

## 📊 Code Metrics Reference (23 Metrics)

### Class-Level Metrics

| Metric | Full Form | Description |
| :--- | :--- | :--- |
| **LOC** | Lines of Code | Total count of source lines within the class body. |
| **NOM** | Number of Methods | Total number of methods defined in the class. |
| **NOPM** | Number of Public Methods | Total number of public methods available in the class interface. |
| **WMC** | Weighted Method Count | Sum of cyclomatic complexities of all methods in the class. |
| **TCC** | Tight Class Cohesion | Relative ratio of method pairs accessing at least one shared class attribute. |
| **WOC** | Weight of Class | Ratio of functional methods to total public methods (excluding getters/setters). |
| **NAS** | Number of Added Services | Number of new public methods added by a subclass (not present in superclass). |
| **PNAS** | Percentage of Newly Added Services | Ratio of added services (`NAS`) relative to total public methods (`NOPM`). |
| **NProtM**| Number of Protected Members | Sum of protected fields and protected methods in the class. |
| **BUR** | Base Class Usage Ratio | Ratio of inherited superclass services actually used via `super` calls. |
| **BOvR** | Base Class Overriding Ratio | Ratio of methods overriding base class implementations. |
| **AMW** | Average Method Weight | Class complexity per method (`WMC / NOM`). |
| **NOPA** | Number of Public Attributes | Total number of public fields exposed directly by the class. |
| **NOAM** | Number of Accessor Methods | Count of getter and setter methods (`get*`, `set*`). |

### Method-Level Metrics

| Metric | Full Form | Description |
| :--- | :--- | :--- |
| **CYCLO** | Cyclomatic Complexity | Count of decision points (`if`, `for`, `while`, `case`, `catch`, `? :`, `&&`, `||`). |
| **MAXNESTING** | Maximum Nesting Level | Deepest nesting depth of control structure blocks within the method. |
| **NOAV** | Number of Accessed Variables | Total distinct local variables and class attributes accessed by the method. |
| **CINT** | Coupling Intensity | Count of distinct foreign methods called directly by this method. |
| **CDISP** | Coupling Dispersion | Ratio of distinct foreign classes invoked relative to total calls (`CINT`). |
| **CM** | Changing Methods | Number of distinct methods calling this method across the project. |
| **CC** | Changing Classes | Number of distinct classes containing methods that invoke this method. |
| **ATFD** | Access To Foreign Data | Count of getter/setter accesses to attributes of other classes. |
| **FDP** | Foreign Data Providers | Number of distinct foreign classes providing data accessed by this method. |
| **LAA** | Locality of Attribute Access | Ratio of local class attribute accesses to total (local + foreign) accesses. |

---

## ☣️ Code Smell Detection Rules & Formulas

The detector checks for **10 classic code smells** using exact empirical rule formulas:

### 1. God Class
A large class that aggregates excessive functionality and accesses foreign data.
- **Rule**: `ATFD > 3 && WMC >= 47 && TCC < 0.33`

### 2. Data Class
A class that acts as a simple data container exposing data via public attributes or accessors with little functional logic.
- **Rule**: `WOC < 0.33 && ((NOPA + NOAM > 3 && WMC < 31) || (NOPA + NOAM > 7 && WMC < 47))`

### 3. Brain Class
A complex class dominated by centralized control logic and high cyclomatic complexity.
- **Rule**: `(BrainMethods > 1 && LOC >= 195 && WMC >= 47 && TCC < 0.5) || (BrainMethods == 1 && LOC >= 390 && WMC >= 94)`

### 4. Brain Method
A method that has grown disproportionately complex, long, and heavily nested.
- **Rule**: `LOC > 65 && CYCLO >= 4 && MAXNESTING >= 3 && NOAV > 7`

### 5. Feature Envy
A method that is more interested in the attributes/data of another class than the class it belongs to.
- **Rule**: `ATFD > 3 && LAA < 0.33 && FDP <= 3`

### 6. Intensive Coupling
A method that makes many calls to a small number of foreign classes.
- **Rule**: `(CINT > 7 && CDISP < 0.5) || (CINT > 3 && CDISP < 0.25 && MAXNESTING > 1)`

### 7. Dispersed Coupling
A method that calls foreign methods distributed across many different foreign classes.
- **Rule**: `CINT > 7 && CDISP >= 0.5 && MAXNESTING > 1`

### 8. Shotgun Surgery
A method whose modification requires widespread changes across multiple classes.
- **Rule**: `CM > 7 && CC > 10`

### 9. Refused Parent Bequest
A subclass that ignores or underutilizes the interface and services provided by its parent class.
- **Rule**: `((NProtM > 3 && BUR < 0.33) || BOvR < 0.33) && ((AMW > 2 || WMC > 14) && NOM > 7)`

### 10. Tradition Breaker
A subclass that introduces a large number of new services without reusing parent class services, disrupting inheritance hierarchy expectations.
- **Rule**: `(NAS >= 7 && PNAS >= 0.67) && ((AMW > 2 || WMC >= 47) && NOM >= 10) && (AMW > 2 && NOM > 5 && WMC >= 24)`

---

## 💻 Local Installation & Setup

### Prerequisites
- **Python 3.8+**
- **pip** package manager

### Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-username/code_smell_detector.git
   cd code_smell_detector
   ```

2. **Create Virtual Environment (Optional but Recommended)**
   ```bash
   # On macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate

   # On Windows:
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Application**
   ```bash
   python app.py
   ```

5. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

---

## 📤 How to Upload to GitHub

Follow these commands to push this codebase to your GitHub repository:

1. Create a new repository on [GitHub](https://github.com/new) named `code-smell-detector` (do not initialize with README since we have one).
2. Open terminal in the project directory and run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of CodeSmell Detector"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/code-smell-detector.git
   git push -u origin main
   ```

---

## 📡 REST API Reference

### 1. Analyze GitHub Repository
- **Endpoint**: `POST /api/analyze/github`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  { "url": "https://github.com/apache/commons-lang" }
  ```

### 2. Analyze Uploaded Files / ZIP
- **Endpoint**: `POST /api/analyze/upload`
- **Headers**: `Content-Type: multipart/form-data`
- **Body**: Form data containing `files` (.java or .zip archives).

### 3. Analyze Raw Java Code
- **Endpoint**: `POST /api/analyze/text`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "filename": "Main.java",
    "content": "public class Main { public static void main(String[] args) {} }"
  }
  ```

---

## 📄 License

This software is developed for educational and academic research purposes under the MIT License.
