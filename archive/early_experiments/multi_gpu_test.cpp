#define CL_HPP_TARGET_OPENCL_VERSION 200
#include <CL/opencl.hpp>
#include <iostream>
#include <vector>

const char* kernel_code = R"(
__kernel void empty_kernel() {
    // No hace nada
}
)";

int main() {
    std::vector<cl::Platform> platforms;
    cl::Platform::get(&platforms);

    if (platforms.empty()) {
        std::cerr << "No OpenCL platforms found.\n";
        return 1;
    }

    for (size_t i = 0; i < platforms.size(); ++i) {
        std::vector<cl::Device> devices;
        platforms[i].getDevices(CL_DEVICE_TYPE_GPU, &devices);

        for (size_t j = 0; j < devices.size(); ++j) {
            cl::Device device = devices[j];
            std::cout << "[GPU " << j << "] " << device.getInfo<CL_DEVICE_NAME>() << "\n";

            cl::Context context(device);
            cl::Program program(context, kernel_code);
            program.build();
            cl::Kernel kernel(program, "empty_kernel");
            cl::CommandQueue queue(context, device);

            // Cargar datos dummy en buffer
            std::vector<int> data(10, j * 10);
            cl::Buffer buffer(context, CL_MEM_READ_WRITE | CL_MEM_COPY_HOST_PTR, sizeof(int) * data.size(), data.data());

            queue.enqueueReadBuffer(buffer, CL_TRUE, 0, sizeof(int), data.data());
            std::cout << "  -> buffer[0] = " << data[0] << "\n";

            // Ejecutar kernel 100000 veces para carga visible en GPU
            for (int i = 0; i < 1000000; ++i) {
                queue.enqueueNDRangeKernel(kernel, cl::NullRange, cl::NDRange(1));
            }
            queue.finish();
        }
    }

    return 0;
}
