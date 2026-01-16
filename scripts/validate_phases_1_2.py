"""
Script de Validacao das Fases 1 e 2
=====================================
Valida que toda a implementacao das Fases 1 (Setup & Infrastructure) e
Fase 2 (Services & Data Layer) foi concluida com sucesso.

Execute com: python scripts/validate_phases_1_2.py
"""

import os
import sys
import importlib.util
from pathlib import Path
from typing import Callable
from datetime import datetime, timedelta

# Adiciona o diretorio backend ao path
BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))


class ValidationResult:
    """Resultado de uma validacao"""
    def __init__(self, name: str, passed: bool, message: str):
        self.name = name
        self.passed = passed
        self.message = message


class PhaseValidator:
    """Validador das Fases 1 e 2"""

    def __init__(self):
        self.results: list[ValidationResult] = []
        self.phase1_checks = 0
        self.phase1_passed = 0
        self.phase2_checks = 0
        self.phase2_passed = 0

    def add_result(self, phase: int, name: str, passed: bool, message: str):
        """Adiciona resultado de validacao"""
        result = ValidationResult(name, passed, message)
        self.results.append(result)

        if phase == 1:
            self.phase1_checks += 1
            if passed:
                self.phase1_passed += 1
        else:
            self.phase2_checks += 1
            if passed:
                self.phase2_passed += 1

    def check_file_exists(self, phase: int, filepath: Path, description: str) -> bool:
        """Verifica se um arquivo existe"""
        exists = filepath.exists()
        self.add_result(
            phase,
            f"Arquivo: {filepath.name}",
            exists,
            f"{'OK' if exists else 'NAO ENCONTRADO'} - {description}"
        )
        return exists

    def check_directory_exists(self, phase: int, dirpath: Path, description: str) -> bool:
        """Verifica se um diretorio existe"""
        exists = dirpath.is_dir()
        self.add_result(
            phase,
            f"Diretorio: {dirpath.name}",
            exists,
            f"{'OK' if exists else 'NAO ENCONTRADO'} - {description}"
        )
        return exists

    def check_class_exists(self, phase: int, module_path: str, class_name: str) -> bool:
        """Verifica se uma classe existe em um modulo"""
        try:
            module = importlib.import_module(module_path)
            has_class = hasattr(module, class_name)
            self.add_result(
                phase,
                f"Classe: {class_name}",
                has_class,
                f"{'OK' if has_class else 'NAO ENCONTRADA'} em {module_path}"
            )
            return has_class
        except Exception as e:
            self.add_result(
                phase,
                f"Classe: {class_name}",
                False,
                f"ERRO ao importar {module_path}: {e}"
            )
            return False

    def check_function_exists(self, phase: int, module_path: str, func_name: str) -> bool:
        """Verifica se uma funcao existe em um modulo"""
        try:
            module = importlib.import_module(module_path)
            has_func = hasattr(module, func_name)
            self.add_result(
                phase,
                f"Funcao: {func_name}",
                has_func,
                f"{'OK' if has_func else 'NAO ENCONTRADA'} em {module_path}"
            )
            return has_func
        except Exception as e:
            self.add_result(
                phase,
                f"Funcao: {func_name}",
                False,
                f"ERRO ao importar {module_path}: {e}"
            )
            return False

    def check_method_exists(self, phase: int, module_path: str, class_name: str, method_name: str) -> bool:
        """Verifica se um metodo existe em uma classe"""
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                has_method = hasattr(cls, method_name)
                self.add_result(
                    phase,
                    f"Metodo: {class_name}.{method_name}",
                    has_method,
                    f"{'OK' if has_method else 'NAO ENCONTRADO'}"
                )
                return has_method
            else:
                self.add_result(
                    phase,
                    f"Metodo: {class_name}.{method_name}",
                    False,
                    f"Classe {class_name} nao encontrada"
                )
                return False
        except Exception as e:
            self.add_result(
                phase,
                f"Metodo: {class_name}.{method_name}",
                False,
                f"ERRO: {e}"
            )
            return False


def validate_phase1(validator: PhaseValidator) -> None:
    """
    Validacao da Fase 1: Setup & Infrastructure

    Arquivos criticos:
    - infrastructure/azure/bicep/main.bicep (opcional se nao usa Azure CLI)
    - backend/app/config.py
    - backend/requirements.txt
    - frontend/package.json
    - backend/.env.example

    Estrutura de diretorios
    """
    print("\n" + "=" * 60)
    print("FASE 1: Setup & Infrastructure")
    print("=" * 60)

    # === ESTRUTURA DE DIRETORIOS ===
    print("\n[Estrutura de Diretorios]")

    dirs_to_check = [
        (BACKEND_DIR / "app", "Diretorio principal do app"),
        (BACKEND_DIR / "app" / "agents", "Diretorio dos agentes"),
        (BACKEND_DIR / "app" / "services", "Diretorio dos servicos"),
        (BACKEND_DIR / "app" / "models", "Diretorio dos modelos"),
        (BACKEND_DIR / "app" / "schemas", "Diretorio dos schemas"),
        (BACKEND_DIR / "app" / "api" / "v1" / "endpoints", "Diretorio dos endpoints"),
        (BACKEND_DIR / "app" / "core", "Diretorio core (auth, websocket)"),
        (BACKEND_DIR / "app" / "utils", "Diretorio de utilitarios"),
        (BACKEND_DIR / "app" / "data", "Diretorio de dados"),
        (BASE_DIR / "frontend", "Diretorio do frontend"),
    ]

    for dirpath, desc in dirs_to_check:
        validator.check_directory_exists(1, dirpath, desc)

    # === ARQUIVOS CRITICOS ===
    print("\n[Arquivos Criticos]")

    files_to_check = [
        (BACKEND_DIR / "app" / "config.py", "Configuracoes centralizadas"),
        (BACKEND_DIR / "app" / "main.py", "Entry point FastAPI"),
        (BACKEND_DIR / "requirements.txt", "Dependencias Python"),
        (BACKEND_DIR / ".env.example", "Template de variaveis de ambiente"),
        (BASE_DIR / "frontend" / "package.json", "Dependencias frontend"),
    ]

    for filepath, desc in files_to_check:
        validator.check_file_exists(1, filepath, desc)

    # === CONFIGURACOES (config.py) ===
    print("\n[Verificacao de Configuracoes]")

    try:
        from app.config import Settings, settings

        # Verificar campos obrigatorios estao definidos no modelo
        required_fields = [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_SPEECH_KEY",
            "AZURE_SPEECH_REGION",
            "COSMOS_DB_ENDPOINT",
            "COSMOS_DB_KEY",
            "SECRET_KEY",
        ]

        model_fields = Settings.model_fields.keys()
        for field in required_fields:
            has_field = field in model_fields
            validator.add_result(
                1,
                f"Config: {field}",
                has_field,
                f"{'OK' if has_field else 'FALTANDO'} - Campo de configuracao"
            )

        # Verificar configuracoes de SRS
        srs_fields = [
            "SRS_INITIAL_INTERVAL_DAYS",
            "SRS_SECOND_INTERVAL_DAYS",
            "SRS_INITIAL_EASE_FACTOR",
            "SRS_MIN_EASE_FACTOR",
        ]

        for field in srs_fields:
            has_field = field in model_fields
            validator.add_result(
                1,
                f"Config SRS: {field}",
                has_field,
                f"{'OK' if has_field else 'FALTANDO'} - Configuracao SRS"
            )

    except Exception as e:
        validator.add_result(1, "Importar config.py", False, f"ERRO: {e}")

    # === FASTAPI SETUP ===
    print("\n[Verificacao FastAPI]")

    try:
        from app.main import app

        validator.add_result(1, "FastAPI app", True, "OK - Aplicacao criada")

        # Verificar CORS
        has_cors = any(
            m.cls.__name__ == "CORSMiddleware"
            for m in app.user_middleware
        )
        validator.add_result(
            1,
            "CORS Middleware",
            has_cors,
            f"{'OK' if has_cors else 'NAO CONFIGURADO'} - Middleware CORS"
        )

        # Verificar rotas basicas
        routes = [route.path for route in app.routes]
        has_root = "/" in routes
        has_health = "/health" in routes

        validator.add_result(1, "Rota /", has_root, "OK - Health check basico")
        validator.add_result(1, "Rota /health", has_health, "OK - Health check detalhado")

    except Exception as e:
        validator.add_result(1, "FastAPI Setup", False, f"ERRO: {e}")

    # === VERIFICAR REQUIREMENTS.TXT ===
    print("\n[Verificacao de Dependencias]")

    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "azure-cosmos",
        "azure-cognitiveservices-speech",
        "openai",
        "langgraph",
        "langchain",
        "websockets",
        "python-jose",
        "passlib",
    ]

    try:
        with open(BACKEND_DIR / "requirements.txt", "r") as f:
            requirements_content = f.read().lower()

        for pkg in required_packages:
            has_pkg = pkg.lower() in requirements_content
            validator.add_result(
                1,
                f"Dependencia: {pkg}",
                has_pkg,
                f"{'OK' if has_pkg else 'FALTANDO'} em requirements.txt"
            )
    except Exception as e:
        validator.add_result(1, "Verificar requirements.txt", False, f"ERRO: {e}")


def validate_phase2(validator: PhaseValidator) -> None:
    """
    Validacao da Fase 2: Services & Data Layer

    Arquivos criticos:
    - backend/app/services/azure_openai_service.py
    - backend/app/services/azure_speech_service.py
    - backend/app/services/cosmos_db_service.py
    - backend/app/models/user.py
    - backend/app/models/vocabulary.py
    - backend/app/models/progress.py
    - backend/app/utils/srs_algorithm.py
    """
    print("\n" + "=" * 60)
    print("FASE 2: Services & Data Layer")
    print("=" * 60)

    # === ARQUIVOS DE SERVICOS ===
    print("\n[Arquivos de Servicos]")

    service_files = [
        (BACKEND_DIR / "app" / "services" / "azure_openai_service.py", "Servico Azure OpenAI"),
        (BACKEND_DIR / "app" / "services" / "azure_speech_service.py", "Servico Azure Speech"),
        (BACKEND_DIR / "app" / "services" / "cosmos_db_service.py", "Servico Cosmos DB"),
    ]

    for filepath, desc in service_files:
        validator.check_file_exists(2, filepath, desc)

    # === ARQUIVOS DE MODELOS ===
    print("\n[Arquivos de Modelos]")

    model_files = [
        (BACKEND_DIR / "app" / "models" / "user.py", "Modelo de Usuario"),
        (BACKEND_DIR / "app" / "models" / "vocabulary.py", "Modelo de Vocabulario"),
        (BACKEND_DIR / "app" / "models" / "grammar.py", "Modelo de Gramatica"),
        (BACKEND_DIR / "app" / "models" / "pronunciation.py", "Modelo de Pronuncia"),
        (BACKEND_DIR / "app" / "models" / "progress.py", "Modelo de Progresso"),
        (BACKEND_DIR / "app" / "models" / "activity.py", "Modelo de Atividade"),
    ]

    for filepath, desc in model_files:
        validator.check_file_exists(2, filepath, desc)

    # === ALGORITMO SRS ===
    print("\n[Algoritmo SRS]")

    validator.check_file_exists(
        2,
        BACKEND_DIR / "app" / "utils" / "srs_algorithm.py",
        "Algoritmo SM-2"
    )

    # === AZURE OPENAI SERVICE ===
    print("\n[Azure OpenAI Service]")

    validator.check_class_exists(2, "app.services.azure_openai_service", "AzureOpenAIService")

    openai_methods = [
        "chat_completion",
        "generate_vocabulary_exercise",
        "evaluate_grammar_explanation",
        "generate_grammar_exercises",
        "generate_conversation_response",
        "detect_grammar_errors",
        "compare_grammar_with_portuguese",
    ]

    for method in openai_methods:
        validator.check_method_exists(
            2,
            "app.services.azure_openai_service",
            "AzureOpenAIService",
            method
        )

    # === AZURE SPEECH SERVICE ===
    print("\n[Azure Speech Service]")

    validator.check_class_exists(2, "app.services.azure_speech_service", "AzureSpeechService")

    speech_methods = [
        "text_to_speech",
        "speech_to_text_from_bytes",
        "pronunciation_assessment",
        "get_phoneme_guidance",
    ]

    for method in speech_methods:
        validator.check_method_exists(
            2,
            "app.services.azure_speech_service",
            "AzureSpeechService",
            method
        )

    # === COSMOS DB SERVICE ===
    print("\n[Cosmos DB Service]")

    validator.check_class_exists(2, "app.services.cosmos_db_service", "CosmosDBService")

    cosmos_methods = [
        "initialize",
        "create_item",
        "get_item",
        "update_item",
        "upsert_item",
        "delete_item",
        "query_items",
        "create_user",
        "get_user",
        "get_vocabulary_progress",
        "update_vocabulary_progress",
        "get_vocabulary_due_for_review",
        "get_grammar_progress",
        "update_grammar_progress",
        "get_pronunciation_progress",
        "update_pronunciation_progress",
        "create_activity",
        "get_pending_activities",
        "create_speaking_session",
        "get_daily_schedule",
        "get_user_statistics",
    ]

    for method in cosmos_methods:
        validator.check_method_exists(
            2,
            "app.services.cosmos_db_service",
            "CosmosDBService",
            method
        )

    # === MODELOS PYDANTIC ===
    print("\n[Modelos Pydantic - User]")

    user_classes = ["UserLevel", "UserProfile", "UserCreate", "User", "UserResponse", "Token"]
    for cls in user_classes:
        validator.check_class_exists(2, "app.models.user", cls)

    print("\n[Modelos Pydantic - Vocabulary]")

    try:
        from app.models import vocabulary
        vocab_classes = [name for name in dir(vocabulary) if not name.startswith("_")]
        has_vocab_models = len([c for c in vocab_classes if "Vocabulary" in c or "Word" in c]) > 0
        validator.add_result(
            2,
            "Modelos Vocabulary",
            has_vocab_models,
            f"{'OK' if has_vocab_models else 'FALTANDO'} - Classes de vocabulario"
        )
    except Exception as e:
        validator.add_result(2, "Modelos Vocabulary", False, f"ERRO: {e}")

    print("\n[Modelos Pydantic - Progress]")

    try:
        from app.models import progress
        progress_classes = [name for name in dir(progress) if not name.startswith("_")]
        has_progress_models = len([c for c in progress_classes if "Progress" in c or "SRS" in c]) > 0
        validator.add_result(
            2,
            "Modelos Progress",
            has_progress_models,
            f"{'OK' if has_progress_models else 'FALTANDO'} - Classes de progresso"
        )
    except Exception as e:
        validator.add_result(2, "Modelos Progress", False, f"ERRO: {e}")

    # === ALGORITMO SRS ===
    print("\n[Algoritmo SRS - Classes e Funcoes]")

    validator.check_class_exists(2, "app.utils.srs_algorithm", "SRSData")
    validator.check_class_exists(2, "app.utils.srs_algorithm", "SRSResult")
    validator.check_class_exists(2, "app.utils.srs_algorithm", "SRSAlgorithm")
    validator.check_function_exists(2, "app.utils.srs_algorithm", "calculate_next_review")
    validator.check_function_exists(2, "app.utils.srs_algorithm", "should_review_low_frequency")

    # === TESTE DO ALGORITMO SRS ===
    print("\n[Teste do Algoritmo SRS]")

    try:
        from app.utils.srs_algorithm import SRSAlgorithm, SRSData

        algorithm = SRSAlgorithm()

        # Teste 1: Primeira revisao correta
        data = SRSData()
        result = algorithm.calculate(data, quality_response=5)

        test1_passed = (
            result.interval == 1 and
            result.repetitions == 1 and
            result.is_correct == True
        )
        validator.add_result(
            2,
            "SRS: Primeira revisao",
            test1_passed,
            f"{'OK' if test1_passed else 'FALHOU'} - intervalo={result.interval}, reps={result.repetitions}"
        )

        # Teste 2: Segunda revisao correta
        data2 = SRSData(
            ease_factor=result.ease_factor,
            interval=result.interval,
            repetitions=result.repetitions,
            next_review=result.next_review
        )
        result2 = algorithm.calculate(data2, quality_response=4)

        test2_passed = (
            result2.interval == 6 and
            result2.repetitions == 2
        )
        validator.add_result(
            2,
            "SRS: Segunda revisao",
            test2_passed,
            f"{'OK' if test2_passed else 'FALHOU'} - intervalo={result2.interval}, reps={result2.repetitions}"
        )

        # Teste 3: Revisao incorreta (reset)
        data3 = SRSData(
            ease_factor=result2.ease_factor,
            interval=result2.interval,
            repetitions=result2.repetitions,
            next_review=result2.next_review
        )
        result3 = algorithm.calculate(data3, quality_response=2)

        test3_passed = (
            result3.interval == 1 and
            result3.repetitions == 0 and
            result3.is_correct == False
        )
        validator.add_result(
            2,
            "SRS: Revisao incorreta",
            test3_passed,
            f"{'OK' if test3_passed else 'FALHOU'} - reset para intervalo=1, reps=0"
        )

        # Teste 4: Verificar quality_from_accuracy
        q5 = algorithm.quality_from_accuracy(95)
        q4 = algorithm.quality_from_accuracy(85)
        q3 = algorithm.quality_from_accuracy(70)
        q2 = algorithm.quality_from_accuracy(50)

        test4_passed = (q5 == 5 and q4 == 4 and q3 == 3 and q2 == 2)
        validator.add_result(
            2,
            "SRS: quality_from_accuracy",
            test4_passed,
            f"{'OK' if test4_passed else 'FALHOU'} - Conversao accuracy->quality"
        )

        # Teste 5: Verificar is_due_for_review
        past_data = SRSData(next_review=datetime.utcnow() - timedelta(days=1))
        future_data = SRSData(next_review=datetime.utcnow() + timedelta(days=1))

        test5_passed = (
            algorithm.is_due_for_review(past_data) == True and
            algorithm.is_due_for_review(future_data) == False
        )
        validator.add_result(
            2,
            "SRS: is_due_for_review",
            test5_passed,
            f"{'OK' if test5_passed else 'FALHOU'} - Verificacao de data de revisao"
        )

    except Exception as e:
        validator.add_result(2, "Testes SRS", False, f"ERRO: {e}")

    # === SINGLETON INSTANCES ===
    print("\n[Singleton Instances]")

    try:
        from app.services.azure_openai_service import azure_openai_service
        validator.add_result(2, "Singleton: azure_openai_service", True, "OK - Instancia criada")
    except Exception as e:
        validator.add_result(2, "Singleton: azure_openai_service", False, f"ERRO: {e}")

    try:
        from app.services.azure_speech_service import azure_speech_service
        validator.add_result(2, "Singleton: azure_speech_service", True, "OK - Instancia criada")
    except Exception as e:
        validator.add_result(2, "Singleton: azure_speech_service", False, f"ERRO: {e}")

    try:
        from app.services.cosmos_db_service import cosmos_db_service
        validator.add_result(2, "Singleton: cosmos_db_service", True, "OK - Instancia criada")
    except Exception as e:
        validator.add_result(2, "Singleton: cosmos_db_service", False, f"ERRO: {e}")

    try:
        from app.utils.srs_algorithm import srs_algorithm
        validator.add_result(2, "Singleton: srs_algorithm", True, "OK - Instancia criada")
    except Exception as e:
        validator.add_result(2, "Singleton: srs_algorithm", False, f"ERRO: {e}")


def print_summary(validator: PhaseValidator) -> bool:
    """Imprime resumo da validacao"""
    print("\n" + "=" * 60)
    print("RESUMO DA VALIDACAO")
    print("=" * 60)

    # Fase 1
    phase1_pct = (validator.phase1_passed / validator.phase1_checks * 100) if validator.phase1_checks > 0 else 0
    phase1_status = "PASSOU" if phase1_pct >= 90 else "FALHOU"
    print(f"\nFASE 1 - Setup & Infrastructure:")
    print(f"  Verificacoes: {validator.phase1_passed}/{validator.phase1_checks} ({phase1_pct:.1f}%)")
    print(f"  Status: {phase1_status}")

    # Fase 2
    phase2_pct = (validator.phase2_passed / validator.phase2_checks * 100) if validator.phase2_checks > 0 else 0
    phase2_status = "PASSOU" if phase2_pct >= 90 else "FALHOU"
    print(f"\nFASE 2 - Services & Data Layer:")
    print(f"  Verificacoes: {validator.phase2_passed}/{validator.phase2_checks} ({phase2_pct:.1f}%)")
    print(f"  Status: {phase2_status}")

    # Total
    total_checks = validator.phase1_checks + validator.phase2_checks
    total_passed = validator.phase1_passed + validator.phase2_passed
    total_pct = (total_passed / total_checks * 100) if total_checks > 0 else 0

    print(f"\nTOTAL:")
    print(f"  Verificacoes: {total_passed}/{total_checks} ({total_pct:.1f}%)")

    # Itens que falharam
    failed = [r for r in validator.results if not r.passed]
    if failed:
        print(f"\n{'=' * 60}")
        print("ITENS QUE FALHARAM:")
        print("=" * 60)
        for r in failed:
            print(f"  - {r.name}: {r.message}")

    # Status final
    all_passed = phase1_pct >= 90 and phase2_pct >= 90

    print(f"\n{'=' * 60}")
    if all_passed:
        print("RESULTADO: VALIDACAO BEM SUCEDIDA!")
        print("As Fases 1 e 2 foram implementadas com sucesso.")
    else:
        print("RESULTADO: VALIDACAO FALHOU")
        print("Corrija os itens listados acima antes de prosseguir para a Fase 3.")
    print("=" * 60)

    return all_passed


def main():
    """Funcao principal"""
    print("\n" + "#" * 60)
    print("# VALIDACAO DAS FASES 1 E 2 DO PROJETO")
    print("# English Learning Multi-Agent App")
    print("#" * 60)
    print(f"\nData: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base Dir: {BASE_DIR}")
    print(f"Backend Dir: {BACKEND_DIR}")

    validator = PhaseValidator()

    # Validar Fase 1
    validate_phase1(validator)

    # Validar Fase 2
    validate_phase2(validator)

    # Imprimir resumo
    success = print_summary(validator)

    # Retornar codigo de saida
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
