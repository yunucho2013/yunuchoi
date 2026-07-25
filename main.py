import flet as ft
import base64
import io
import json
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
        src="https://via.placeholder.com/300x300/f0f0f0/000000?text=Take+a+Selfie",
        width=250,
        height=250,
        fit="cover",
        border_radius=10,
    )

    status_text = ft.Text("", size=14, color="#000000", weight="bold")
    progress_ring = ft.ProgressRing(visible=False, color="#000000")

    # [복구된 기능] Base64 사진 수신 및 미리보기 처리
    def on_image_received(e):
        nonlocal selected_image_bytes
        if e.data:
            try:
                # 자바스크립트에서 보낸 JSON 데이터를 파싱
                data = json.loads(e.data)
                b64_string = data.get("image", "")
                
                if b64_string:
                    b64_data = b64_string.split(",")[-1] if "," in b64_string else b64_string
                    raw_bytes = base64.b64decode(b64_data)
                    
                    img = Image.open(io.BytesIO(raw_bytes))
                    img.thumbnail((800, 800))
                    
                    buffer = io.BytesIO()
                    img.convert("RGB").save(buffer, format="JPEG", quality=85)
                    selected_image_bytes = buffer.getvalue()

                    img_preview.src_base64 = base64.b64encode(selected_image_bytes).decode('utf-8')
                    img_preview.src = None
                    status_text.value = "📸 셀카 촬영 완료!"
                    status_text.color = "#2e7d32"
                else:
                    status_text.value = "⚠️ 이미지 데이터를 받지 못했습니다."
                    status_text.color = "#d32f2f"
            except Exception as err:
                status_text.value = f"⚠️ 이미지 처리 실패: {str(err)}"
                status_text.color = "#d32f2f"
            page.update()

    # 파이썬과 자바스크립트 간의 통신 채널 설정
    page.on_java_script_message = on_image_received

    # [복구된 버튼] 📸 스마트폰/태블릿 전면 카메라 즉시 호출
    # 최신 브라우저 보안 정책을 준수하는 정석 HTML5 호출 방식입니다.
    def take_photo_click(e):
        status_text.value = "카메라를 켜는 중..."
        page.update()
        
        # 브라우저에게 셀카 카메라를 켜라고 명령하는 자바스크립트
        camera_script = """
        (function() {
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.setAttribute('capture', 'user'); // 전면 카메라(셀카) 강제
            input.style.display = 'none';

            input.onchange = function(evt) {
                var file = evt.target.files[0];
                if (!file) return;
                var reader = new FileReader();
                reader.onload = function(e_reader) {
                    // 촬영된 Base64 데이터를 Flet(파이썬)으로 전송
                    window.flet_javaScriptMessage(JSON.stringify({
                        "image": e_reader.target.result
                    }));
                };
                reader.readAsDataURL(file);
            };

            document.body.appendChild(input);
            input.click(); // 사용자가 버튼을 누른 것처럼 시뮬레이션
            input.remove(); // 사용 후 제거
        })();
        """
        page.run_javascript(camera_script)

    btn_take_photo = ft.ElevatedButton(
        "📸 지금 바로 셀카 찍기",
        icon="camera_alt",
        on_click=take_photo_click,
        bgcolor="#000000",
        color="#ffffff",
        width=360,
        height=50
    )

    # URL 입력창 및 적용
    img_url_input = ft.TextField(
        label="🖼️ 이미지 URL 주소 입력",
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
            try:
                img_preview.src = img_url_input.value
                img_preview.src_base64 = None
                selected_image_bytes = None
                status_text.value = "✅ URL 이미지 적용 완료!"
                status_text.color = "#2e7d32"
            except Exception as err:
                status_text.value = f"⚠️ URL 이미지 적용 실패: {str(err)}"
                status_text.color = "#d32f2f"
            page.update()

    btn_apply_url = ft.OutlinedButton("적용", on_click=apply_url_image)

    result_card = ft.Container(
        content=ft.Column([
            ft.Text("📊 AI 외모 평가 결과", size=18, weight="bold", color="#000000"),
            ft.Divider(color="#eeeeee"),
            ft.Text("사진을 적용하고 분석을 시작하세요.", size=14, color="#666666")
        ]),
        padding=20,
        bgcolor="#f0f0f0",
        border_radius=10,
        visible=False,
        width=360,
    )

    # Gemini AI 분석 함수
    def analyze_face(e):
        nonlocal selected_image_bytes

        if not api_key_input.value:
            status_text.value = "⚠️ Gemini API Key를 입력해주세요!"
            status_text.color = "#d32f2f"
            page.update()
            return

        if not selected_image_bytes and not img_url_input.value:
            status_text.value = "⚠️ 먼저 셀카를 찍거나 이미지 URL을 입력해주세요!"
            status_text.color = "#d32f2f"
            page.update()
            return

        btn_scan.disabled = True
        progress_ring.visible = True
        status_text.value = "이목구비 스캔 중..."
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
                # URL 이미지 다운로드 (CORS 이슈 주의)
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

    page.add(
        ft.Column([
            header_title,
            header_sub,
            ft.Divider(height=10, color="#eeeeee"),
            api_key_input,
            ft.Container(height=5),
            img_preview,
            ft.Container(height=5),
            btn_take_photo, # 복구된 버튼 배치
            ft.Row([img_url_input, btn_apply_url], width=360, alignment="center"),
            ft.Container(height=10),
            btn_scan,
            progress_ring,
            status_text,
            result_card,
        ], horizontal_alignment="center", spacing=10)
    )

ft.app(target=main, view=ft.AppView.WEB_BROWSER)
