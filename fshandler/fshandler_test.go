package fshandler

import (
	"errors"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/darkwyrm/anselusd/config"
	"github.com/google/uuid"
)

// setupTest initializes the global config and resets the workspace directory
func setupTest() error {

	// In this case we don't care about the diceware wordlist returned. Note that
	// resetWorkspaceDir depends on initialization of the server config, so this call must go
	// first
	config.SetupConfig()

	err := resetWorkspaceDir()
	if err != nil {
		return err
	}

	return nil
}

// resetWorkspaceDir empties out the workspace directory to make sure it's ready for a filesystem
// test. Because the workspace directory may have special permissions set on it, we can't just
// delete the directory and recreate it--we have to actually empty the directory.
func resetWorkspaceDir() error {
	var anpath LocalAnPath
	err := anpath.Set("/")
	if err != nil {
		return err
	}

	handle, err := os.Open(anpath.ProviderPath())
	if err != nil {
		return err
	}
	defer handle.Close()

	entries, err := handle.Readdirnames(-1)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		err = os.RemoveAll(filepath.Join(anpath.ProviderPath(), entry))
		if err != nil {
			return err
		}
	}
	return nil
}

// generateRandomFile creates a random file filled with zeroes which can be as small as 100 bytes
// and as large as 10k
func generateRandomFile(dir string, size int) (string, error) {
	if size > 10240 || size < 100 {
		return "", errors.New("Size out of range")
	}

	var anpath LocalAnPath
	err := anpath.Set(dir)
	if err != nil {
		return "", err
	}

	_, err = os.Stat(anpath.ProviderPath())
	if err != nil && !os.IsNotExist(err) {
		return "", err
	}

	filedata := make([]byte, size, size)
	for j := range filedata {
		filedata[j] = 48
	}
	filename := GenerateFileName(size)

	path := filepath.Join(anpath.ProviderPath(), filename)
	err = ioutil.WriteFile(path, filedata, 0777)
	if err != nil {
		return "", err
	}
	fmt.Printf("Wrote file %s\n", filename)

	return filename, nil
}

func makeTestFiles(dir string, count int) error {
	if count > 50 || count < 1 {
		return errors.New("File count out of range")
	}

	var anpath LocalAnPath
	err := anpath.Set(dir)
	if err != nil {
		return err
	}

	_, err = os.Stat(anpath.ProviderPath())
	if err != nil && !os.IsNotExist(err) {
		return err
	}

	for i := 0; i < count; i++ {
		filesize := rand.Intn(10140) + 100
		_, err = generateRandomFile(anpath.AnselusPath(), filesize)
		if err != nil {
			return err
		}
		time.Sleep(time.Millisecond * 500)
	}
	return nil
}

// MakeTestDirectories creates a number of randomly-named directories and returns their names
func makeTestDirectories(path string, count int) ([]string, error) {
	if count > 50 || count < 1 {
		return nil, errors.New("Count out of range")
	}

	var anpath LocalAnPath
	err := anpath.Set(path)
	if err != nil {
		return nil, err
	}

	_, err = os.Stat(anpath.ProviderPath())
	if err != nil && !os.IsNotExist(err) {
		return nil, err
	}

	names := make([]string, count)
	for i := 0; i < count; i++ {
		dirname := uuid.New().String()
		dirpath := filepath.Join(anpath.ProviderPath(), dirname)
		err := os.Mkdir(dirpath, 0777)
		if err != nil {
			return nil, err
		}
	}
	return names, nil
}

// ensureTestDirectory makes sure a specific test directory exists. The path is expected to be
// an Anselus-format path, resulting in a path relative to the workspace root.
func ensureTestDirectory(path string) error {
	var anpath LocalAnPath
	err := anpath.Set(path)
	if err != nil {
		return err
	}

	_, err = os.Stat(anpath.ProviderPath())
	if err != nil && !os.IsNotExist(err) {
		return err
	}

	return os.Mkdir(anpath.ProviderPath(), 0777)
}

func TestLocalFSProvider_Exists(t *testing.T) {
	err := setupTest()
	if err != nil {
		t.Fatalf("TestLocalFSProvider_Exists: Couldn't reset workspace dir: %s", err.Error())
	}

	wid := "11111111-1111-1111-1111-111111111111"
	testFile := "1613915806.1251.850ff5d0-a191-4f4e-8104-a71db98296a3"
	testPath := strings.Join([]string{"/", wid, testFile}, " ")

	err = ensureTestDirectory("/ " + wid)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_Exists: Couldn't create wid: %s", err.Error())
	}

	provider := NewLocalProvider()

	// Subtest #1: bad path
	_, err = provider.Exists("/var/anselus/" + wid)
	if err == nil {
		t.Fatal("TestLocalFSProvider_Exists: failed to handle bad path")
	}

	// Subtest #2: nonexistent file
	exists, err := provider.Exists(testPath)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_Exists: subtest #2 unexpected error: %s", err.Error())
	}
	if exists {
		t.Fatal("TestLocalFSProvider_Exists: failed to handle nonexistent file")
	}

	// Subtest #3: actual file -- success
	testFile, err = generateRandomFile("/ "+wid, 1024)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_Exists: subtest #3 unexpected error: %s", err.Error())
	}

	testPath = strings.Join([]string{"/", wid, testFile}, " ")
	exists, err = provider.Exists(testPath)
	if !exists {
		t.Fatal("TestLocalFSProvider_Exists: failed to handle file existence")
	}
}

func TestLocalFSProvider_MakeDirectory(t *testing.T) {
	err := setupTest()
	if err != nil {
		t.Fatalf("TestLocalFSProvider_MakeDirectory: Couldn't reset workspace dir: %s", err.Error())
	}

	wid := "11111111-1111-1111-1111-111111111111"
	wid2 := "22222222-2222-2222-2222-222222222222"
	provider := NewLocalProvider()

	// Subtest #1: bad path
	err = provider.MakeDirectory("/var/anselus/" + wid)
	if err == nil {
		t.Fatal("TestLocalFSProvider_MakeDirectory: failed to handle bad path")
	}

	// Subtest #2: actual success
	err = provider.MakeDirectory("/ " + wid)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_MakeDirectory: subtest #2 failed to create dir: %s",
			err.Error())
	}

	// Subtest #3: directory already exists
	err = provider.MakeDirectory("/ " + wid)
	if err == nil {
		t.Fatalf("TestLocalFSProvider_MakeDirectory: subtest #3 failed to handle existing dir: %s",
			err.Error())
	}

	// Subtest #4: recursive creation

	testDir := strings.Join([]string{"/", wid, wid2}, " ")
	err = provider.MakeDirectory(testDir)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_MakeDirectory: subtest #4 failed to recursive create dir: %s",
			err.Error())
	}
}

func TestLocalFSProvider_RemoveDirectory(t *testing.T) {
	err := setupTest()
	if err != nil {
		t.Fatalf("TestLocalFSProvider_RemoveDirectory: Couldn't reset workspace dir: %s", err.Error())
	}

	wid := "11111111-1111-1111-1111-111111111111"
	wid2 := "22222222-2222-2222-2222-222222222222"
	provider := NewLocalProvider()

	// Subtest #1: bad path

	err = provider.MakeDirectory("/var/anselus/" + wid)
	if err == nil {
		t.Fatal("TestLocalFSProvider_RemoveDirectory: failed to handle bad path")
	}

	// Subtest #2: directory doesn't exist

	err = provider.RemoveDirectory("/ "+wid, false)
	if err == nil {
		t.Fatalf("TestLocalFSProvider_RemoveDirectory: subtest #2 failed to handle nonexistent dir: %s",
			err.Error())
	}

	// Subtest #3: actual success

	err = provider.MakeDirectory("/ " + wid)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_RemoveDirectory: subtest #3 failed to create dir: %s",
			err.Error())
	}
	err = provider.RemoveDirectory("/ "+wid, false)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_RemoveDirectory: subtest #3 failed to remove dir: %s",
			err.Error())
	}

	// Subtest #4: recursive removal

	testDir := strings.Join([]string{"/", wid, wid2}, " ")
	err = provider.MakeDirectory(testDir)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_RemoveDirectory: subtest #4 failed to create dir: %s",
			err.Error())
	}
	err = makeTestFiles(testDir, 1)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_RemoveDirectory: subtest #4 failed to test files: %s",
			err.Error())
	}
	err = provider.RemoveDirectory(testDir, true)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_RemoveDirectory: subtest #4 failed to remove dir: %s",
			err.Error())
	}
}

func TestLocalFSProvider_ListFiles(t *testing.T) {
	err := setupTest()
	if err != nil {
		t.Fatalf("TestLocalFSProvider_ListFiles: Couldn't reset workspace dir: %s", err.Error())
	}

	wid := "11111111-1111-1111-1111-111111111111"
	testPath := "/ " + wid
	provider := NewLocalProvider()

	// Subtest #1: bad path

	err = provider.MakeDirectory("/var/anselus/" + wid)
	if err == nil {
		t.Fatal("TestLocalFSProvider_ListFiles: failed to handle bad path")
	}

	// Subtest #2: directory doesn't exist

	_, err = provider.ListFiles(testPath, 0)
	if err == nil {
		t.Fatalf("TestLocalFSProvider_ListFiles: subtest #2 failed to handle nonexistent dir: %s",
			err.Error())
	}

	// Subtest #3: empty directory

	err = provider.MakeDirectory("/ " + wid)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_ListFiles: subtest #3 failed to create test dir: %s",
			err.Error())
	}
	testFiles, err := provider.ListFiles(testPath, 0)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_ListFiles: subtest #3 unexpected error: %s",
			err.Error())
	}
	if len(testFiles) > 0 {
		t.Fatal("TestLocalFSProvider_ListFiles: subtest #3 failed to handle empty directory")
	}

	// Subtest #4: actual success

	err = makeTestFiles(testPath, 3)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_ListFiles: subtest #4 unexpected error making test files: %s",
			err.Error())
	}
	testFiles, err = provider.ListFiles(testPath, 0)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_ListFiles: subtest #4 unexpected error listing files: %s",
			err.Error())
	}
	if len(testFiles) != 3 {
		t.Fatal("TestLocalFSProvider_ListFiles: subtest #4 bad file count")
	}

	// Subtest #5: path is a file

	_, err = provider.ListFiles(testPath+" "+testFiles[0], 0)
	if err == nil {
		t.Fatalf("TestLocalFSProvider_ListFiles: subtest #5 failed to handle path to file: %s",
			err.Error())
	}

	// Subtest #6: filtered file listing
	time.Sleep(time.Second)
	timeFilter := time.Now().Unix()
	err = makeTestFiles(testPath, 2)

	testFiles, err = provider.ListFiles(testPath, timeFilter)
	if err != nil {
		t.Fatalf("TestLocalFSProvider_ListFiles: subtest #6 unexpected error listing files: %s",
			err.Error())
	}
	if len(testFiles) != 2 {
		t.Fatal("TestLocalFSProvider_ListFiles: subtest #6 bad filtered file count")
	}

}

func TestLocalFSProvider_ListDirectories(t *testing.T) {
}

func TestLocalFSProvider_MakeTempFile(t *testing.T) {
}

func TestLocalFSProvider_InstallTempFile(t *testing.T) {
}

func TestLocalFSProvider_MoveFile(t *testing.T) {
}

func TestLocalFSProvider_CopyFile(t *testing.T) {
}

func TestLocalFSProvider_DeleteFile(t *testing.T) {
}

func TestLocalFSProvider_OpenFile(t *testing.T) {
}

func TestLocalFSProvider_ReadFile(t *testing.T) {
}

func TestLocalFSProvider_CloseFile(t *testing.T) {
}
