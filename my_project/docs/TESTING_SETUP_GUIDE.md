# Testing Setup Guide
## YouTube Downloader - Comprehensive Testing Implementation

### 🎯 **Quick Start**

#### **1. Install Test Dependencies**
```bash
# Navigate to project directory
cd my_project

# Install test dependencies
python run_tests.py install
# OR manually:
pip install -e .[test]
```

#### **2. Run Basic Tests**
```bash
# Run all tests
python run_tests.py all

# Run only unit tests (fast)
python run_tests.py unit

# Run only integration tests  
python run_tests.py integration

# Run fast tests (exclude slow network tests)
python run_tests.py fast
```

#### **3. View Coverage Report**
After running tests, open `htmlcov/index.html` in your browser to see detailed coverage.

---

## 📋 **Test Structure Overview**

### **Directory Organization**
```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                    # Pytest settings
├── unit/                          # Fast, isolated component tests
│   ├── test_core.py              # Core video processing tests
│   ├── test_transcript_processor.py  # Text processing tests
│   ├── test_metadata_collector.py    # Content analysis tests
│   └── test_utils/               # Utility function tests
├── integration/                   # Component interaction tests
│   ├── test_cli_workflows.py     # End-to-end CLI tests
│   ├── test_download_workflows.py    # Download process tests
│   └── test_export_workflows.py      # Export functionality tests
├── fixtures/                      # Mock data and responses
│   ├── mock_responses/           # Captured API responses
│   └── sample_configs/           # Test configuration files
└── test_data/                     # Static test assets
    ├── test_urls.json            # Curated stable test URLs
    └── expected_outputs/         # Expected file contents
```

---

## 🧪 **Test Categories & Execution**

### **Unit Tests** (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (< 1 second each)  
- **Dependencies**: No network, mocked external calls
- **Coverage**: Core business logic, error handling

```bash
# Run all unit tests
pytest tests/unit/ -v -m unit

# Run specific unit test file
pytest tests/unit/test_core.py -v

# Run with coverage
pytest tests/unit/ --cov=src/my_project --cov-report=term
```

### **Integration Tests** (`tests/integration/`)
- **Purpose**: Test component interactions and workflows
- **Speed**: Medium (< 30 seconds each)
- **Dependencies**: May use network mocks, file system
- **Coverage**: End-to-end user workflows

```bash
# Run all integration tests  
pytest tests/integration/ -v -m integration

# Run CLI workflow tests
pytest tests/integration/test_cli_workflows.py -v

# Skip slow tests
pytest tests/integration/ -v -m "integration and not slow"
```

### **Network Tests** 
- **Purpose**: Test real network interactions (use sparingly)
- **Speed**: Slow (may take minutes)
- **Dependencies**: Internet connection, stable test URLs
- **Coverage**: Real API interactions, network error handling

```bash
# Run network tests (requires internet)
pytest tests/ -v -m network

# Skip network tests (for offline development)
pytest tests/ -v -m "not network"
```

---

## 🎨 **Test Markers**

Use pytest markers to categorize and filter tests:

```python
@pytest.mark.unit          # Fast unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.slow          # Tests that take longer
@pytest.mark.network       # Tests requiring internet
@pytest.mark.cli           # CLI interface tests
```

### **Running Specific Test Categories**
```bash
# Only unit tests
pytest -m unit

# Integration tests excluding slow ones
pytest -m "integration and not slow"

# All tests except network tests
pytest -m "not network"

# CLI tests only
pytest -m cli
```

---

## 🔧 **Key Testing Patterns**

### **Using Fixtures**
Tests use shared fixtures from `conftest.py`:

```python
def test_video_info_extraction(mock_video_info, temp_config_dir):
    """Example test using shared fixtures."""
    # mock_video_info provides realistic video data
    # temp_config_dir provides isolated configuration
    
def test_transcript_processing(sample_transcript_data):
    """Test using sample transcript data."""
    # sample_transcript_data provides consistent test content
```

### **Mocking External Dependencies**
```python
@patch('src.my_project.core.YoutubeDL')
def test_with_mocked_ydl(mock_ydl):
    """Test with mocked yt-dlp dependency."""
    mock_instance = Mock()
    mock_instance.extract_info.return_value = {...}
    mock_ydl.return_value.__enter__.return_value = mock_instance
```

### **Testing CLI Commands**
```python
def test_cli_command(cli_runner):
    """Test CLI command execution."""
    result = cli_runner.invoke(main, ['--help'])
    assert result.exit_code == 0
    assert 'usage:' in result.output
```

---

## 📊 **Coverage Requirements**

### **Target Coverage Levels**
- **Unit Tests**: 90%+ of core modules
- **Integration Tests**: 80%+ of workflow paths  
- **Critical Functions**: 100% (error handling, file operations)

### **Coverage Commands**
```bash
# Generate HTML coverage report
pytest --cov=src/my_project --cov-report=html

# Terminal coverage report
pytest --cov=src/my_project --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov=src/my_project --cov-fail-under=80
```

### **Viewing Coverage Reports**
- **HTML Report**: Open `htmlcov/index.html` in browser
- **Terminal Report**: Shows missing lines directly in console

---

## 🚀 **Development Workflow**

### **During Active Development**
```bash
# Fast feedback loop - unit tests only
python run_tests.py unit

# Before committing changes
python run_tests.py fast

# Before creating pull request
python run_tests.py all
```

### **Test-Driven Development (TDD)**
1. **Write failing test** for new functionality
2. **Implement minimal code** to make test pass
3. **Refactor** while keeping tests green
4. **Repeat** for next feature

### **Adding New Tests**
1. **Choose test type**: Unit vs Integration
2. **Use appropriate fixtures** from `conftest.py`
3. **Follow naming conventions**: `test_*` functions
4. **Add appropriate markers**: `@pytest.mark.unit`, etc.
5. **Ensure test isolation**: Tests should not depend on each other

---

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **Import Errors**
```bash
# Install package in development mode
pip install -e .

# Check Python path
python -c "import sys; print(sys.path)"
```

#### **Fixture Not Found**
```bash
# Check conftest.py is in test directory
# Verify fixture name spelling
# Ensure fixture is properly decorated with @pytest.fixture
```

#### **Tests Running Slowly**
```bash
# Run fast tests only
pytest -m "not slow"

# Run specific test file
pytest tests/unit/test_core.py

# Use more specific test selection
pytest tests/unit/test_core.py::TestVideoInfoExtraction::test_extract_video_info_valid_url
```

#### **Coverage Report Missing**
```bash
# Install coverage dependencies
pip install pytest-cov

# Ensure src path is correct
pytest --cov=src/my_project --cov-report=term
```

### **Test Data Management**

#### **Updating Test URLs**
- Periodically verify URLs in `test_data/test_urls.json` are still valid
- Replace with equivalent content if videos become unavailable
- Document changes in test data for team awareness

#### **Mock Data Maintenance**  
- Update mock responses when API responses change
- Keep fixture data realistic and representative
- Version mock data when making significant changes

---

## 📈 **Continuous Integration**

### **GitHub Actions Configuration** (Future)
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e .[test]
      - run: pytest tests/ --cov=src/my_project --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### **Pre-commit Hooks** (Recommended)
```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

---

## ✅ **Success Criteria**

### **Framework Setup Complete When:**
- ✅ All test dependencies installed without errors
- ✅ Basic test suite runs and passes
- ✅ Coverage reports generate successfully  
- ✅ Test execution time under 5 minutes
- ✅ Both unit and integration tests functional

### **Test Implementation Complete When:**
- ✅ 90%+ coverage on core modules
- ✅ All critical workflows tested
- ✅ Error conditions properly tested
- ✅ Performance benchmarks established
- ✅ CI/CD pipeline operational

---

**This testing framework provides a solid foundation for ensuring the reliability and quality of your YouTube downloader application. The modular structure allows for incremental implementation while maintaining high confidence in core functionality.**
