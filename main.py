import flet as ft
from google import genai
from google.genai import types

def main(page: ft.Page):
    # 📱 기본 화면 설정 (라이트 / 화이트 테마)
    page.title = "외모 점수 측정 앱"
    page.window_icon = "app_icon.png"
    page.window_width = 420
    page.window_height = 850
    page.bgcolor = "#ffffff"  # 완전한 화이트
    page.theme_mode = "light"
    page.scroll = "adaptive"

    selected_file_path = None

    # ==========================================
    #  UI 헤더 (화이트 & 블랙)
    # ==========================================
    header_title = ft.Text("외모 점수 측정 앱", size=24, weight="bold", color="#000000")
    header_sub = ft.Text("개성/분위기 제외. 오직 이목구비와 비율만 평가합니다.", size=12, color="#666666")

    # API Key 입력창
    api_key_input = ft.TextField(
        label="🔑 Gemini API Key 입력",
        hint_text="API 키를 입력하세요",
        password=True,
        can_reveal_password=True,
        border_color="#000000",
        focused_border_color="#000000",
        label_style=ft.TextStyle(color="#555555"),
        color="#000000"
    )

    # ==========================================
    # 이미지 업로드 영역
    # ==========================================
    img_preview = ft.Image(
        src="https://via.placeholder.com/300x300/f0f0f0/000000?text=No+Image",
        width=250,
        height=250,
        fit="cover",
        border_radius=10,
    )

    selected_file_text = ft.Text("선택된 파일 없음", size=12, color="#888888")

    # 파일 선택 함수 (최신 비동기 방식)
    async def pick_files_click(e):
        nonlocal selected_file_path
        files = await ft.FilePicker().pick_files(
            allow_multiple=False,
            allowed_extensions=["jpg", "jpeg", "png", "webp"]
        )
        if files and len(files) > 0:
            selected_file_path = files[0].path
            selected_file_text.value = f"📄 {files[0].name}"
            img_preview.src = selected_file_path
            page.update()

    btn_pick_file = ft.OutlinedButton(
        "📷 사진 선택",
        icon="photo_library",
        on_click=pick_files_click,
        style=ft.ButtonStyle(
            color="#000000",
            side=ft.BorderSide(1, "#000000"),
        )
    )

    # ==========================================
    # AI 스캔 및 결과 표시 영역
    # ==========================================
    progress_ring = ft.ProgressRing(visible=False, color="#000000")
    status_text = ft.Text("", size=14, color="#000000", weight="bold")

    # AI 결과 카드 (화이트 배경 + 블랙 테두리)
    result_card = ft.Container(
        content=ft.Column([
            ft.Text("📊 AI 외모 평가 결과", size=18, weight="bold", color="#000000"),
            ft.Divider(color="#eeeeee"),
            ft.Text("사진을 선택하고 분석 시작하기.", size=14, color="#666666")
        ]),
        padding=20,
        bgcolor="#f9f9f9",
        border=ft.Border.all(1, "#000000"),
        border_radius=10,
        visible=False,
        width=360,
    )

    # ==========================================
    # Gemini AI 로직 (100% 면상/이목구비 전용 독설 프롬프트)
    # ==========================================
    def analyze_face(e):
        nonlocal selected_file_path
        
        if not api_key_input.value:
            status_text.value = "⚠️ Gemini API Key를 입력해주세요!"
            status_text.color = "#d32f2f"
            page.update()
            return

        if not selected_file_path:
            status_text.value = "⚠️ 분석할 사진을 먼저 선택해주세요!"
            status_text.color = "#d32f2f"
            page.update()
            return

        btn_scan.disabled = True
        progress_ring.visible = True
        status_text.value = "스캔 중..."
        status_text.color = "#000000"
        result_card.visible = False
        page.update()

        try:
            with open(selected_file_path, "rb") as f:
                image_bytes = f.read()

            client = genai.Client(api_key=api_key_input.value)

            prompt = """
            당신은 피도 눈물도 없는 냉정한 외모 및 얼굴 비율 평가 AI입니다.
            
            [절대 준수 규칙]:
            1. '개성 있다', '매력 있다', '분위기 있다', '인상이 좋다', '친근하다' 같은 위선적이거나 돌려 말하는 평가 표현은 절대 금지합니다.
            2. 패션, 헤어스타일, 조명, 옷차림, 개성 다 빼고 '오직 눈, 코, 입, 얼굴형, 대칭 및 황금 비율'만 가지고 냉정하게 외모 점수를 매기세요.
            3. 객관적으로 못생겼거나 비율이 안 맞으면 절대로 돌려 말하지 말고 30점~50점대로 감점 폭격을 날리세요. (진짜 잘생기거나 예쁜 경우에만 80~90점대 부여)

            [답변 양식]:
            1. [얼굴 외모 점수]: (0점 ~ 100점 사이의 냉정한 점수)
            2. [AI의 냉정한 한줄평]: (돌려 말하지 않고 이목구비 상태를 직설적으로 표현한 한 줄)
            3. [이목구비 정밀 팩폭]: (눈의 크기와 비율, 코의 모양, 입술, 얼굴형, 대칭성에 대한 냉정한 비평 3줄)
            4. [가장 심각한 감점 요인]: (눈, 코, 입, 비율 중 가장 점수를 깎아먹은 부위)
            """

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg",
                    ),
                    prompt,
                ]
            )

            result_card.content = ft.Column([
                ft.Text("AI 분석 완료", size=18, weight="bold", color="#000000"),
                ft.Divider(color="#cccccc"),
                ft.Text(response.text, size=14, color="#111111", selectable=True),
            ], spacing=10)
            
            result_card.visible = True
            status_text.value = "🎉 스캔 완료!"

        except Exception as ex:
            status_text.value = f"❌ 오류 발생: {str(ex)}"
            status_text.color = "#d32f2f"

        finally:
            btn_scan.disabled = False
            progress_ring.visible = False
            page.update()

    # 블랙 버튼 + 흰색 글씨
    btn_scan = ft.ElevatedButton(
        "AI 스캔 시작",
        on_click=analyze_face,
        bgcolor="#000000",
        color="#ffffff",
        height=50,
        width=360,
    )

    # ==========================================
    # 메인 레이아웃 통합
    # ==========================================
    page.add(
        ft.Column([
            header_title,
            header_sub,
            ft.Divider(height=10, color="#eeeeee"),
            api_key_input,
            ft.Container(height=5),
            img_preview,
            selected_file_text,
            btn_pick_file,
            ft.Container(height=10),
            btn_scan,
            progress_ring,
            status_text,
            result_card,
        ], horizontal_alignment="center", spacing=10)
    )

# 기존 코드 대신 아래 코드로 교체!
ft.app(target=main, view=ft.AppView.WEB_BROWSER, assets_dir="assets")
