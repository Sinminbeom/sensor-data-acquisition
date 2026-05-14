import base64
import sys

if __name__ == '__main__':
    # 첫번째 arg를 받아옴
    if len(sys.argv) < 2:
        print("Usage: python main.py [filename]")
        sys.exit(1)
    input_file_name = sys.argv[1]

    # 파일을 읽어옴
    try:
        with open(input_file_name, 'rb') as binary_file:
            binary_data = binary_file.read()
    except FileNotFoundError:
        print("File not found")
        sys.exit(1)

    # 읽어온 바이너리 데이터를 Base64로 인코딩
    encoded_data = base64.b64encode(binary_data)

    # 출력 파일 이름 설정
    # input_file_name에서 확장자를 제거
    output_file_name = input_file_name.split('.')[0]
    output_file_name = output_file_name + '.b64'

    # 인코딩된 데이터를 텍스트 형태로 .b64 파일에 저장
    with open(output_file_name, 'w') as encoded_file:
        # Python 3에서 base64.b64encode는 bytes를 반환하기 때문에,
        # 파일에 쓰기 전에 문자열로 변환
        encoded_file.write(encoded_data.decode('utf-8'))
