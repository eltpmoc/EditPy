"""Abra este arquivo no EditPy e use Executar ou Debug."""

from dataclasses import dataclass


@dataclass
class Project:
    name: str
    language: str = "Python"

    def greeting(self) -> str:
        return f"Bem-vindo ao {self.name}. Vamos criar algo incrível com {self.language}!"


def main():
    project = Project("EditPy")
    print(project.greeting())
    for step in range(1, 4):
        print(f"Etapa {step}: pronto para desenvolver.")


if __name__ == "__main__":
    main()
