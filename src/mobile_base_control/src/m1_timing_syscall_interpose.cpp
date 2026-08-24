// Copyright 2026 mobile_base contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <sys/syscall.h>
#include <unistd.h>

namespace mobile_base_control::detail
{
void observe_serial_write_before(int fd);
void observe_serial_write_after(int fd);
void observe_serial_read_return(int fd, ssize_t result);
}  // namespace mobile_base_control::detail

extern "C" ssize_t write(int fd, const void * buffer, size_t count)
{
  mobile_base_control::detail::observe_serial_write_before(fd);
  const ssize_t result = static_cast<ssize_t>(::syscall(SYS_write, fd, buffer, count));
  mobile_base_control::detail::observe_serial_write_after(fd);
  return result;
}

extern "C" ssize_t read(int fd, void * buffer, size_t count)
{
  const ssize_t result = static_cast<ssize_t>(::syscall(SYS_read, fd, buffer, count));
  mobile_base_control::detail::observe_serial_read_return(fd, result);
  return result;
}
