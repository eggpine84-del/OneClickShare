# [파일명]: main_b.py (단발성 타격 템플릿 - 스케줄러/크론용) | [원칙] 기승전결 구역 준수, 로직 끝에 12세 수준 요약 주석 필수
# [체크] 1. 에러 경로에 log_error(...) 누락 방지 | 2. 1회성 실행 후 깔끔하게 프로세스 종료(퇴근) 필수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import logging,asyncio,os,time; from typing import Dict,Any,Tuple,Optional
LOG_FILE_PATH,ERR_VAL_CODE,ERR_VAL_MSG,ERR_SYSTEM_CODE='logs/cron_error.log',"VAL_ERR_01","입력 데이터가 올바르지 않거나 비어 있습니다.","SYS_ERR_99"
os.makedirs(os.path.dirname(LOG_FILE_PATH),exist_ok=True) # 로그 폴더 자동 생성 방어 코드
logging.basicConfig(filename=LOG_FILE_PATH,level=logging.ERROR,format='%(asctime)s - %(levelname)s - %(message)s'); default_logger=logging.getLogger("CronLogger")

async def log_error(code:str,message:str,logger:logging.Logger=default_logger)->None:
    """Logs system errors. Args: code(str), message(str), logger(logging.Logger)."""
    logger.error(f"[{code}] {message}") # [요약] 프로그램이 일하다가 실수한 내용을 외부에서 넘겨받은 '로그 메모장(logger)'에 안전하게 적어두는 기능입니다!
async def validate_and_prepare_input(raw_data:Optional[Dict[str,Any]])->Tuple[bool,Optional[Dict[str,Any]],str]:
    """Validates runtime input type."""
    if not isinstance(raw_data,dict): await log_error(ERR_VAL_CODE,ERR_VAL_MSG); return False,None,ERR_VAL_MSG # [체크 1] 에러 기록 누락 방지
    return True,raw_data,"검증 통과" # [요약] 들어온 상자가 찌그러지지 않은 올바른 상자(딕셔너리)인지 문지기처럼 꼼꼼하게 검사했습니다!
async def process_core_behavior(validated_data:Dict[str,Any])->Dict[str,Any]:
    """Executes business operations asynchronously."""
    try: return {"success":True,"result":{**validated_data,"processed_at":"2026-07-20"},"error":""} # [요약] 진짜 해야 할 중요한 일(연산/저장)을 원본 데이터의 훼손 없이 안전하게 마쳤습니다!
    except Exception as e: await log_error(ERR_SYSTEM_CODE,f"핵심 로직 실행 중 오류 발생: {e}"); return {"success":False,"result":None,"error":f"핵심 로직 실행 중 오류 발생: {e}"} # [체크 1] 에러 기록 누락 방지
async def run_main_workflow(raw_input:Optional[Dict[str,Any]])->Dict[str,Any]:
    """Coordinates the entire workflow lifecycle (Async Native)."""
    is_valid,clean_data,error_message=await validate_and_prepare_input(raw_input)
    if not is_valid: return {"success":False,"result":None,"error":error_message}
    return await process_core_behavior(clean_data)

def run_main_workflow_sync(raw_input:Optional[Dict[str,Any]])->Dict[str,Any]:
    """Provides a synchronous wrapper for legacy or synchronous environments."""
    try: loop=asyncio.get_running_loop()
    except RuntimeError: loop=None
    if loop and loop.is_running(): raise RuntimeError("이미 루프가 돌고 있습니다. await run_main_workflow()를 사용하세요.")
    return asyncio.run(run_main_workflow(raw_input)) 
    # [요약] 매니저가 비동기 손님과 동기 손님 모두를 안전하게 맞이할 수 있도록 최종 출구를 두 개로 만든 결말 구역입니다!

# ================= (히트 앤드 런 단발성 실행 구역) =================
# [체크] 윈도우 작업 스케줄러나 Cron이 이 파일을 호출할 때 1회성으로 도는 실무 구역입니다.
if __name__=="__main__":
    print("= [히트 앤드 런] 단발성 자동화 스크립트 가동 시작 =\n")
    start_time = time.time() # 작업 시작 시간 기록
    
    # 실무에서는 이 부분에 엑셀 파일 경로나 오늘 날짜 등을 payload로 쏴줍니다.
    job_payload = {"task_name": "daily_excel_report", "target": "대성무역_발주서"}
    
    print("[*] 메인 작업 실행 중...")
    final_result = run_main_workflow_sync(job_payload)
    
    elapsed_time = time.time() - start_time # 소요 시간 계산
    
    if final_result.get("success"):
        print(f"✅ 작업 성공! (소요 시간: {elapsed_time:.2f}초)\n - 결과: {final_result['result']}")
    else:
        print(f"❌ 작업 실패! (소요 시간: {elapsed_time:.2f}초)\n - 에러: {final_result['error']}")
        
    print("\n🚀 모든 임무를 완수했습니다. 봇 대기 없이 스크립트를 즉시 완전 종료(퇴근)합니다.")