#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include "rs_driver/api/lidar_driver.hpp"
#include "rs_driver/msg/point_cloud_msg.hpp"

namespace py = pybind11;
using namespace robosense::lidar;

typedef PointXYZI PointT;
typedef PointCloudT<PointT> PointCloudMsg;


class RSBPConverter {
private:
  LidarDriver<PointCloudMsg>& _driver;

  SyncQueue<std::shared_ptr<PointCloudMsg>> free_cloud_queue;
  SyncQueue<std::shared_ptr<PointCloudMsg>> stuffed_cloud_queue;

  std::thread _handle_thread;
  bool _is_exit = false;

  std::mutex _frame_mutex;
  std::vector<double> _frame;

public:
  RSBPConverter(const pybind11::dict& params)
    : _driver(*new LidarDriver<PointCloudMsg>())
  {
    RSDriverParam param;                  ///< Create a parameter object

    param.input_type = InputType::ONLINE_LIDAR;
    param.lidar_type = LidarType::RSBP;

    if (params.contains("msop_port"))
      param.input_param.msop_port = params["msop_port"].cast<int>();

    if (params.contains("difop_port"))
      param.input_param.difop_port = params["difop_port"].cast<int>();
    
    if (params.contains("min_distance"))
      param.decoder_param.min_distance = params["min_distance"].cast<float>();
    
    if (params.contains("max_distance"))
      param.decoder_param.max_distance = params["max_distance"].cast<float>();
    
    if (params.contains("start_angle"))
      param.decoder_param.start_angle = params["start_angle"].cast<float>();

    if (params.contains("end_angle"))
      param.decoder_param.end_angle = params["end_angle"].cast<float>();

    if (params.contains("extrinsic")) {
      if (params["extrinsic"].contains("x"))
        param.decoder_param.transform_param.x = params["extrinsic"]["x"].cast<double>();
      if (params["extrinsic"].contains("y"))
        param.decoder_param.transform_param.y = params["extrinsic"]["y"].cast<double>();
      if (params["extrinsic"].contains("z"))
        param.decoder_param.transform_param.z = params["extrinsic"]["z"].cast<double>();
      if (params["extrinsic"].contains("roll"))
        param.decoder_param.transform_param.roll = params["extrinsic"]["roll"].cast<double>();
      if (params["extrinsic"].contains("pitch"))
        param.decoder_param.transform_param.pitch = params["extrinsic"]["pitch"].cast<double>();
      if (params["extrinsic"].contains("yaw"))
        param.decoder_param.transform_param.yaw = params["extrinsic"]["yaw"].cast<double>();
    }

    _driver.regPointCloudCallback(
      [&] {
        std::shared_ptr<PointCloudMsg> msg = free_cloud_queue.pop();
        if (msg.get() != NULL)
          return msg;

        return std::make_shared<PointCloudMsg>();
      },
      [&](std::shared_ptr<PointCloudMsg> msg) {
        stuffed_cloud_queue.push(msg);
      }
    );

    _driver.regExceptionCallback(
      [](const Error& code) {
        std::cerr << "Error code: " << code.toString() << std::endl;
      }
    );

    _driver.init(param);
  }

  void start() {
    _driver.start();
    _handle_thread = std::thread([&]() { process_points(); });
  }

  void stop() {
    _driver.stop();
    _is_exit = true;
    _handle_thread.join();
  }

  void process_points(void) {
    while (!_is_exit) {
      std::shared_ptr<PointCloudMsg> msg = stuffed_cloud_queue.popWait();
      if (msg.get() == NULL)
        continue;
      
      _frame_mutex.lock();

      _frame.clear();
      _frame.reserve(msg->points.size() * 3);

      const float threshold_distance = 20.0;
      const float threshold_distance_squared = threshold_distance * threshold_distance;

      for (const auto& point : msg->points) {
        if (point.x == 0 && point.y == 0 && point.z == 0)
          continue;
        _frame.push_back(point.x);
        _frame.push_back(point.y);
        _frame.push_back(point.z);

        float distance_squared = point.x * point.x + point.y * point.y;
        if (distance_squared > threshold_distance_squared) {
          intensity_to_color(point.intensity, _frame);
        }
        else {
          float scale_factor = distance_squared / threshold_distance_squared;
          uint8_t norm_intensity = static_cast<uint8_t>(std::min(static_cast<int>(point.intensity * scale_factor), 255));
          intensity_to_color(norm_intensity, _frame);
        }
      }

      _frame_mutex.unlock();

      free_cloud_queue.push(msg);
    }
  }

  void intensity_to_color(uint8_t intensity, std::vector<double>& frame) {
    static const uint8_t range[3] = {15, 40, 255};
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
    return py::array_t<double>(_frame.size(), _frame.data());
  }
};


PYBIND11_MODULE(rsbp_converter, m) {
  py::class_<RSBPConverter>(m, "RSBPConverter")
    .def(py::init<const pybind11::dict&>())
    .def("start", &RSBPConverter::start)
    .def("stop", &RSBPConverter::stop)
    .def("snapshot_pcd", &RSBPConverter::snapshot_pcd);
}
