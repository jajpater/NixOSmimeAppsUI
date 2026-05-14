{
  description = "Textual TUI for declarative MIME app management in a NixOS/Home Manager repo";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.python3Packages.buildPythonApplication {
            pname = "nixos-mimeapps-ui";
            version = "0.1.0";
            pyproject = true;
            src = ./.;
            propagatedBuildInputs = with pkgs.python3Packages; [
              textual
            ];
            nativeBuildInputs = with pkgs.python3Packages; [
              setuptools
            ];
            nativeCheckInputs = with pkgs.python3Packages; [
              pytest
            ];
            checkPhase = ''
              pytest
            '';
          };
        });

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/nixos-mimeapps-ui";
        };
      });

      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python3
              python3Packages.textual
              python3Packages.pytest
            ];
          };
        });
    };
}
