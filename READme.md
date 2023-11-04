# paragraph = """
# Đài truyền thanh thị trấn Rừng Thông xin kính chào toàn thể nhân dân, mời toàn thể nhân dân đón nghe, chương trình phát thanh hôm nay gồm những nội dung sau:
# 1.	Bài tuyên truyền chung sức xây dựng đô thị văn minh. 
# 2.	Bản tin tuyên truyền về phát động toàn dân tham gia phong trào: Nhà tôi có bình chữa cháy trên địa bàn thị trấn Rừng Thông.
# 3.	Thông báo tuyên truyền Hụi, họ, biêu, phường và những hệ lụy khôn lường.
# 4.	Thông báo đấu giá Quyền sử dụng đất gồm 51 lô đất ở tại khu dân cư thị trấn Rừng Thông, huyện Đông Sơn, Mặt bằng quy hoạch số 4132, 2742, 1879.
# 5.	Thông báo Thanh niên khám tuyển nghĩa vụ quân sự tại huyện năm 2024.
# Sau đây là nội dung chi tiết.
# """

# docs = segment_doc(paragraph)

# with ProcessPoolExecutor(max_workers=1) as executor:
#     futures = (executor.submit(infer, doc) for doc in docs)

#     wavs = []
#     for future in as_completed(futures):
#         wav = future.result()
#         wavs.append(wav)
        
# waveform = np.concatenate(wavs)
# sf.write("test.wav", waveform, samplerate=22050)
