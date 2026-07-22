import flet as ft
import base64
import io
from PIL import Image
from google import genai
from google.genai import types

def main(page: ft.Page):
    page.title = "외모 점수 측정 앱"
    page.window_width = 420
    page.window_height = 850
    page.bgcolor = "#ffffff"
    page.theme_mode = "light"
    page.scroll = "adaptive"

    selected_image_bytes = None

    header_title = ft.Text("외모 점수 측정 앱", size=24, weight="bold", color="#000000")
    header_sub = ft.Text("개성/분위기 제외. 오직 이목구비와 비율만 평가합니다.", size=12, color="#666666")

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

    img_preview = ft.Image(
        src="https://via.placeholder.com/300x300/f0f0f0/000000?text=Preview",
        width=250,
        height=250,
        fit="cover",
        border_radius=10,
    )

    status_text = ft.Text("", size=14, color="#000000", weight="bold")
    progress_ring = ft.ProgressRing(visible=False, color="#000000")

    # 1. 최신 Flet 웹 전용 FilePicker 이벤트 등록
    def handle_picker_result(e: ft.FilePickerResultEvent):
        nonlocal selected_image_bytes
        if e.files and len(e.files) > 0:
            file = e.files[0]
            
            # 브라우저 파일 바이트 가져오기
            raw_data = getattr(file, "bytes", None)
            
            if raw_data:
                try:
                    img = Image.open(io.BytesIO(raw_data))
                    img.thumbnail((800, 800))
                    
                    buffer = io.BytesIO()
                    img.convert("RGB").save(buffer, format="JPEG", quality=85)
                    selected_image_bytes = buffer.getvalue()

                    base64_img = base64.b64encode(selected_image_bytes).decode('utf-8')
                    img_preview.src_base64 = base64_img
                    img_preview.src = None
                    status_text.value = f"✅ 갤러리 사진('{file.name}') 로드 성공!"
                    status_text.color = "#2e7d32"
                except Exception as img_err:
                    status_text.value = f"⚠️ 이미지 변환 오류: {str(img_err)}"
                    status_text.color = "#d32f2f"
            else:
                status_text.value = "⚠️ 브라우저가 파일 데이터를 읽지 못했습니다. 아래 URL로 시도해보세요!"
                status_text.color = "#d32f2f"

            page.update()

    # 2. FilePicker 인스턴스 생성 및 이벤트 바인딩
    file_picker = ft.FilePicker()
    file_picker.on_result = handle_picker_result

    # 3. 📷 갤러리 버튼 생성!
    btn_pick_file = ft.ElevatedButton(
        "📷 갤러리에서 사진 선택",
        icon="photo_library",
        on_click=lambda _: file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
            with_data=True
        ),
        bgcolor="#000000",
        color="#ffffff",
        width=360,
        height=45
    )

    # URL 입력 영역
    img_url_input = ft.TextField(
        label="🖼️ 이미지 URL 주소 (보조용)",
        hint_text="https://...",
        border_color="#000000",
        focused_border_color="#000000",
        label_style=ft.TextStyle(color="#555555"),
        color="#000000",
        expand=True
    )

    def apply_url_image(e):
        nonlocal selected_image_bytes
        if img_url_input.value:
            img_preview.src = img_url_input.value
            img_preview.src_base64 = None
            selected_image_bytes = None
            status_text.value = "✅ URL 이미지 적용 완료!"
            status_text.color = "#2e7d32"
            page.update()

    btn_apply_url = ft.OutlinedButton("URL 적용", on_click=apply_url_image)

    result_card = ft.Container(
        content=ft.Column([
            ft.Text("📊 AI 외모 평가 결과", size=18, weight="bold", color="#000000"),
            ft.Divider(color="#eeeeee"),
            ft.Text("사진을 선택하고 분석 시작하기.", size=14, color="#666666")
        ]),
        padding=20,
        bgcolor="#f0f0f0",
        border_radius=10,
        visible=False,
        width=360,
    )

    # Gemini 분석
    def analyze_face(e):
        nonlocal selected_image_bytes

        if not api_key_input.value:
            status_text.value = "⚠️ Gemini API Key를 입력해주세요!"
            status_text.color = "#d32f2f"
            page.update()
            return

        if not selected_image_bytes and not img_url_input.value:
            status_text.value = "⚠️ 갤러리 사진을 고르거나 URL을 입력해주세요!"
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

            if selected_image_bytes:
                content_part = types.Part.from_bytes(
                    data=selected_image_bytes,
                    mime_type="image/jpeg",
                )
            else:
                import urllib.request
                req = urllib.request.Request(
                    img_url_input.value, 
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                image_data = urllib.request.urlopen(req).read()
                content_part = types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/jpeg",
                )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[content_part, prompt]
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

    btn_scan = ft.ElevatedButton(
        "AI 스캔 시작",
        on_click=analyze_face,
        bgcolor="#000000",
        color="#ffffff",
        height=50,
        width=360,
    )

    # 4. 웹 오버레이에 FilePicker 등록 (빨간 오류 없이 안전하게 탑재)
    page.overlay.clear()
    page.overlay.append(file_picker)

    page.add(
        ft.Column([
            header_title,
            header_sub,
            ft.Divider(height=10, color="#eeeeee"),
            api_key_input,
            ft.Container(height=5),
            img_preview,
            btn_pick_file, # 🎉 갤러리 버튼 등장!
            ft.Row([img_url_input, btn_apply_url], width=360, alignment="center"),
            ft.Container(height=10),
            btn_scan,
            progress_ring,
            status_text,
            result_card,
        ], horizontal_alignment="center", spacing=10)
    )

ft.app(target=main, view=ft.AppView.WEB_BROWSER, assets_dir="assets")
