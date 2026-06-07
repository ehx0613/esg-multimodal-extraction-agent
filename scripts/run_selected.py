from config.settings import RAW_DATA_DIR, REPORTS_DIR
from pipeline.appendix_pipeline import ESGAppendixPipeline
from utils.raw_pdf_utils import find_raw_pdf_by_name


SELECTED_FILES = [
    #"000858_浜擾绮甠娑瞋2024_浜擾绮甠娑诧細2024骞村害鐜銆佺ぞ浼氬強鍏徃娌荤悊锛圗SG锛夋姤鍛?pdf",
    "002083_瀛氭棩鑲′唤_2025_瀛氭棩鑲′唤锛氱ぞ浼氳矗浠绘姤鍛?pdf",
]


def main():
    for filename in SELECTED_FILES:
        pdf_path = find_raw_pdf_by_name(RAW_DATA_DIR, filename)

        if pdf_path is None:
            print(f"鉂?鎵句笉鍒?PDF: {filename}")
            continue

        report_dir = REPORTS_DIR / pdf_path.stem

        print("\n" + "=" * 100)
        print(f"寮€濮嬪鐞? {filename}")
        print("=" * 100)

        ESGAppendixPipeline(report_dir).run(pdf_path)

        print(f"鉁?瀹屾垚: {filename}")
        print(f"杈撳嚭鐩綍: {report_dir}")


if __name__ == "__main__":
    main()
