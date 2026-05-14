#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include "hesai_lidar_sdk_fix.hpp"

namespace py = pybind11;

struct PointXYZT {
  double x;
  double y;
  double z;
  double timestamp;
};

struct PointXYZIT {
  double x;
  double y;
  double z;
  uint8_t intensity;
  double timestamp;
};


class At128Converter {
private:
  HesaiLidarSdk<PointXYZIT>& _driver;
  std::mutex _frame_mutex;
  LidarDecodedFrame<PointXYZIT>& _frame;
  ssize_t _size_per_point = sizeof(PointXYZIT) / sizeof(double);

public:
  At128Converter(const pybind11::dict& params)
    : _driver(*new HesaiLidarSdk<PointXYZIT>())
    , _frame(*new LidarDecodedFrame<PointXYZIT>())
  {
    DriverParam param;

    // assign param
    param.input_param.source_type = DATA_FROM_LIDAR;
    param.input_param.ptc_port = 9347;

    param.input_param.correction_file_path = "/app/drivers/AT128/HesaiLidar_SDK_2.0/correction/angle_correction/AT128E2X_Angle Correction File.dat";
    param.input_param.firetimes_path = "/app/drivers/AT128/HesaiLidar_SDK_2.0/correction/firetime_correction/AT128E2X_Firetime Correction File.csv";

    if (params.contains("device_ip_address"))
      param.input_param.device_ip_address = params["device_ip_address"].cast<std::string>();

    if (params.contains("udp_port"))
      param.input_param.udp_port = params["udp_port"].cast<int>();

    if (params.contains("extrinsic")) {
      param.decoder_param.transform_param.x = params["extrinsic"]["x"].cast<double>();
      param.decoder_param.transform_param.y = params["extrinsic"]["y"].cast<double>();
      param.decoder_param.transform_param.z = params["extrinsic"]["z"].cast<double>();
      param.decoder_param.transform_param.roll = params["extrinsic"]["roll"].cast<double>();
      param.decoder_param.transform_param.pitch = params["extrinsic"]["pitch"].cast<double>();
      param.decoder_param.transform_param.yaw = params["extrinsic"]["yaw"].cast<double>();
    }

    _driver.Init(param);

    uint32_t socket_buffer_size = 262144000;
    _driver.lidar_ptr_->source_->SetSocketBufferSize(socket_buffer_size);

    // Assign the callback function
    _driver.RegRecvCallback([&](const LidarDecodedFrame<PointXYZIT>& new_frame) {
      std::lock_guard<std::mutex> lock(_frame_mutex);
      _frame = new_frame;
    });
  }

  void start() {
    // Start the process thread
    _driver.Start();
  }

  void stop() {
    _driver.Stop();
  }

  inline void intensity_to_color(uint8_t intensity, std::vector<double>& frame) {
    static const uint8_t range[3] = {4, 20, 255};
    // 강도에 따라 색상을 다르게 조절
    if (intensity < range[0]) { // 강도가 낮음, 파란색
      frame.push_back(0);   // r
      frame.push_back(0);   // g
      frame.push_back(255); // b
    } else if (intensity < range[1]) { // 강도가 중간, 녹색
      frame.push_back(0);   // r
      frame.push_back(255); // g
      frame.push_back(0);   // b
    } else { // 강도가 높음, 빨간색
      frame.push_back(255); // r
      frame.push_back(0);   // g
      frame.push_back(0);   // b
    }
  }

  py::array_t<double> snapshot_pcd() {
    std::lock_guard<std::mutex> lock(_frame_mutex);

    std::vector<double> frame;
    frame.reserve(_frame.points_num * _size_per_point);

    const float threshold_distance = 20.0;
    const float threshold_distance_squared = threshold_distance * threshold_distance;

    for (size_t i = 0; i < _frame.points_num; i++) {
      PointXYZIT& point = _frame.points[i];
      if (point.x == 0 && point.y == 0 && point.z == 0)
        continue;
      frame.push_back(point.x);
      frame.push_back(point.y);
      frame.push_back(point.z);

      float distance_squared = point.x * point.x + point.y * point.y;
      if (distance_squared > threshold_distance_squared) {
        intensity_to_color(point.intensity, frame);
      }
      else {
        float scale_factor = distance_squared / threshold_distance_squared;
        uint8_t norm_intensity = static_cast<uint8_t>(std::min(static_cast<int>(point.intensity * scale_factor), 255));
        intensity_to_color(norm_intensity, frame);
      }
    }

    return py::array_t<double>(frame.size(), frame.data());
  }
};


PYBIND11_MODULE(at128_converter, m) {
  py::class_<At128Converter>(m, "At128Converter")
    .def(py::init<const pybind11::dict&>())
    .def("start", &At128Converter::start, "A function that starts the lidar")
    .def("stop", &At128Converter::stop, "A function that stops the lidar")
    .def("snapshot_pcd", &At128Converter::snapshot_pcd, "A function that returns the point cloud data");
}
