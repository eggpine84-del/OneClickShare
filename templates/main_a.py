# [파일명]: main.py (대장 템플릿 - 메인 실행 파일용) | [원칙] 기승전결 구역 준수, 로직 끝에 12세 수준 요약 주석 필수
# [체크] 1. 에러 경로에 log_error(...) 누락 방지 | 2. 배포 전 __main__ 테스트 코드 주석/삭제 필수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import logging,asyncio,os; from typing import Dict,Any,Tuple,Optional
LOG_FILE_PATH,ERR_VAL_CODE,ERR_VAL_MSG,ERR_SYSTEM_CODE='logs/process_error.log',"VAL_ERR_01","입력 데이터가 올바르지 않거나 비어 있습니다.","SYS_ERR_99"
os.makedirs(os.path.dirname(LOG_FILE_PATH),exist_ok=True) # 로그 폴더 자동 생성 방어 코드
logging.basicConfig(filename=LOG_FILE_PATH,level=logging.ERROR,format='%(asctime)s - %(levelname)s - %(message)s'); default_logger=logging.getLogger("SystemLogger")

async def log_error(code:str,message:str,logger:logging.Logger=default_logger)->None:
    """Logs system errors. Args: code(str), message(str), logger(logging.Logger)."""
    logger.error(f"[{code}] {message}") # [요약] 프로그램이 일하다가 실수한 내용을 외부에서 넘겨받은 '로그 메모장(logger)'에 안전하게 적어두는 기능입니다!
async def validate_and_prepare_input(raw_data:Optional[Dict[str,Any]])->Tuple[bool,Optional[Dict[str,Any]],str]:
    """Validates runtime input type."""
    if not isinstance(raw_data,dict): await log_error(ERR_VAL_CODE,ERR_VAL_MSG); return False,None,ERR_VAL_MSG # [체크 1] 에러 기록 누락 방지
    return True,raw_data,"검증 통과" # [요약] 들어온 상자가 찌그러지지 않은 올바른 상자(딕셔너리)인지 문지기처럼 꼼꼼하게 검사했습니다!
async def process_core_behavior(validated_data:Dict[str,Any])->Dict[str,Any]:
    """Executes business operations asynchronously."""
    try: return {"success":True,"result":{**validated_data,"processed_at":"2026-07-15"},"error":""} # [요약] 진짜 해야 할 중요한 일(연산/저장)을 원본 데이터의 훼손 없이 안전하게 마쳤습니다!
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

# ================= (동기/비동기 다 품는 유니버설 테스트 구역) =================
# [체크 2] 배포 전 아래 테스트 코드는 주석 처리하거나 삭제하세요.
if __name__=="__main__":
    print("= [기승전결] 유니버설 모듈 단독 가동 테스트 =\n\n[*] 1. 비동기(Async) 환경 테스트 (Native)")
    async def _run_async_tests():
        res_suc,res_fail=await asyncio.gather(run_main_workflow({'test_key':'async_value'}),run_main_workflow(None))
        print(f"  - 성공 케이스 결과: {res_suc}\n  - 실패 케이스 결과: {res_fail}")
    asyncio.run(_run_async_tests())
    print("\n[*] 2. 동기(Sync) 브릿지 환경 테스트 (Wrapper)\n  - 성공 케이스 결과:",run_main_workflow_sync({'test_key':'sync_value'}),"\n  - 실패 케이스 결과:",run_main_workflow_sync(None))
    _bot=globals().get('bot')
    if _bot:
        print("\n🚀 3. 테스트 완료! 이 프로그램은 [봇/서버]로 판단되어 24시간 상시 대기 모드로 전환합니다.")
        _polling=getattr(_bot,'infinity_polling',getattr(_bot,'polling',None))
        if asyncio.iscoroutinefunction(_polling) if _polling else False: print("  -> 비동기 봇 루프(asyncio) 시작"); asyncio.run(_bot.infinity_polling(allowed_updates=['message','edited_message'],skip_pending=True))
        elif hasattr(_bot,'infinity_polling'): print("  -> 동기 봇 루프(infinity_polling) 시작"); _bot.infinity_polling(skip_pending=True)
        elif hasattr(_bot,'polling'): print("  -> 동기 봇 루프(polling) 시작"); _bot.polling(none_stop=True)
        else: print("  -> 에러: 유효한 봇 폴링(Polling) 메서드를 찾을 수 없습니다.")
    else: print("\n✅ 모든 모듈 테스트 완료! 봇 인스턴스가 없으므로 안전하게 종료합니다.")