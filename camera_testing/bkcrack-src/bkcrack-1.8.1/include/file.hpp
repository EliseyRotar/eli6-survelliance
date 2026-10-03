#ifndef BKCRACK_FILE_HPP
#define BKCRACK_FILE_HPP

#include "types.hpp"

#include <fstream>

/// Exception thrown if a file cannot be opened
class FileError : public BaseError
{
public:
    /// Constructor
    explicit FileError(const std::string& description);
};

/// \brief Open an input file stream
/// \exception FileError if the file cannot be opened
auto openInput(const std::string& filename) -> std::ifstream;

/// Load at most \a size bytes from an input stream
auto loadStream(std::istream& is, std::size_t size) -> std::vector<std::uint8_t>;

/// \brief Open an output file stream
/// \exception FileError if the file cannot be opened
auto openOutput(const std::string& filename) -> std::ofstream;

#endif // BKCRACK_FILE_HPP
